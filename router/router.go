package router

import (
	"encoding/json"
	"io"
	"net/http"
	// "strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/juzeon/poe-openai-proxy/conf"
	"github.com/juzeon/poe-openai-proxy/poe"
	"github.com/juzeon/poe-openai-proxy/util"
)

func contains(s []string, v string) bool {
	for _, item := range s {
		if item == v {
			return true
		}
	}
	return false
}

func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// authorization := c.GetHeader("Authorization")
		// token := strings.Replace(authorization, "Bearer ", "", 1)
		// if !contains(conf.Conf.AccessTokens, token) {
		// 	c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		// 	c.Abort()
		// 	return
		// }
		c.Next()
	}
}

func Setup(engine *gin.Engine) {
	getModels := func(c *gin.Context) {
		SetCORS(c)
		c.JSON(http.StatusOK, conf.Models)
	}

	engine.GET("/models", AuthMiddleware(), getModels)
	engine.GET("/v1/models", AuthMiddleware(), getModels)

	postCompletions := func(c *gin.Context) {
		//SetCORS(c)
		var req poe.CompletionRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(400, "bad request")
			return
		}
		for _, msg := range req.Messages {
			if msg.Role != "system" && msg.Role != "user" && msg.Role != "assistant" {
				c.JSON(400, "role of message validation failed: "+msg.Role)
				return
			}
		}
		client, err := poe.GetClient()
		if err != nil {
			c.JSON(500, err)
			return
		}
		defer client.Release()
		if req.Stream {
			util.Logger.Info("stream using client: " + client.Token)
			Stream(c, req, client)
		} else {
			util.Logger.Info("ask using client: " + client.Token)
			Ask(c, req, client)
		}
	}

	engine.POST("/chat/completions", AuthMiddleware(), postCompletions)
	engine.POST("/v1/chat/completions", AuthMiddleware(), postCompletions)

	// OPTIONS /v1/chat/completions

	optionsCompletions := func(c *gin.Context) {
		SetCORS(c)
		c.JSON(200, "")
	}

	engine.OPTIONS("/chat/completions", optionsCompletions)
	engine.OPTIONS("/v1/chat/completions", optionsCompletions)
}

func Stream(c *gin.Context, req poe.CompletionRequest, client *poe.Client) {
	c.Writer.Header().Set("Content-Type", "text/event-stream")
	c.Writer.Header().Set("Cache-Control", "no-cache")
	c.Writer.Header().Set("Connection", "keep-alive")
	w := c.Writer
	flusher, _ := w.(http.Flusher)
	timeout := time.Duration(conf.Conf.Timeout) * time.Second
	ticker := time.NewTimer(timeout)
	defer ticker.Stop()
	channel, err := client.Stream(req.Messages, req.Model)
	if err != nil {
		c.JSON(500, err.Error())
		return
	}

	conversationID := "chatcmpl-" + util.RandStringRunes(29)

	createSSEResponse := func(content string, haveRole bool) {
		done := content == "[DONE]"
		var finishReason *string
		delta := map[string]string{}
		if done {
			_str := "stop"
			finishReason = &_str
		} else if haveRole {
			delta["role"] = "assistant"
		} else {
			delta["content"] = content
		}
		data := poe.CompletionSSEResponse{
			Choices: []poe.SSEChoice{{
				Index:        0,
				Delta:        delta,
				FinishReason: finishReason,
			}},
			Created: time.Now().Unix(),
			Id:      conversationID,
			Model:   req.Model,
			Object:  "chat.completion.chunk",
		}
		dataV, _ := json.Marshal(&data)
		_, err := io.WriteString(w, "data: "+string(dataV)+"\n\n")
		if err != nil {
			util.Logger.Error(err)
		}
		flusher.Flush()
		if done {
			_, err := io.WriteString(w, "data: [DONE]\n\n")
			if err != nil {
				util.Logger.Error(err)
			}
			flusher.Flush()
		}
	}
	createSSEResponse("", true)
forLoop:
	for {
		select {
		case <-ticker.C:
			c.SSEvent("error", "timeout")
			break forLoop
		case d := <-channel:
			ticker.Reset(timeout)
			createSSEResponse(d, false)
			if d == "[DONE]" {
				break forLoop
			}
		}
	}
}

func Ask(c *gin.Context, req poe.CompletionRequest, client *poe.Client) {
	message, err := client.Ask(req.Messages, req.Model)
	if err != nil {
		c.JSON(500, err.Error())
		return
	}
	c.JSON(200, poe.CompletionResponse{
		ID:      "chatcmpl-" + util.RandStringRunes(29),
		Object:  "chat.completion",
		Created: int(time.Now().Unix()),
		Choices: []poe.Choice{{
			Index:        0,
			Message:      *message,
			FinishReason: "stop",
		}},
		Usage: poe.Usage{
			PromptTokens:     0,
			CompletionTokens: 0,
			TotalTokens:      0,
		},
	})
}

func SetCORS(c *gin.Context) {
	c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
	c.Writer.Header().Set("Access-Control-Allow-Headers", "*")
	c.Writer.Header().Set("Access-Control-Allow-Methods", "*")
	c.Writer.Header().Set("Access-Control-Max-Age", "86400")
	c.Writer.Header().Set("Content-Type", "application/json")
}
