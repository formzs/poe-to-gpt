package conf

import (
	"github.com/pelletier/go-toml/v2"
	"os"
	"strings"
)

type ConfigStruct struct {
	Port          int               `toml:"port"`
	Tokens        []string          `toml:"tokens"`
	AccessTokens  []string          `toml:"accessTokens"`
	Gateway       string            `toml:"gateway"`
	Bot           map[string]string `toml:"bot"`
	SimulateRoles int               `toml:"simulate-roles"`
	RateLimit     int               `toml:"rate-limit"`
	CoolDown      int               `toml:"cool-down"`
	Timeout       int               `toml:"timeout"`
}

type ModelDef struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int    `json:"created"`
	OwnedBy string `json:"owned_by"`
}

type ModelsResp struct {
	Object string     `json:"object"`
	Data   []ModelDef `json:"data"`
}

func (c ConfigStruct) GetGatewayWsURL() string {
	str := strings.ReplaceAll(c.Gateway, "http://", "ws://")
	str = strings.ReplaceAll(str, "https://", "wss://")
	return str
}

var Conf ConfigStruct

var Models ModelsResp

func Setup() {
	v, err := os.ReadFile("config.toml")
	if err != nil {
		panic(err)
	}
	err = toml.Unmarshal(v, &Conf)
	if err != nil {
		panic(err)
	}
	if Conf.Port == 0 {
		Conf.Port = 3700
	}
	if Conf.RateLimit == 0 {
		Conf.RateLimit = 10
	}
	if Conf.Bot == nil {
		Conf.Bot = map[string]string{
			"gpt-3.5-turbo-16k":    "ChatGPT-16k",
			"gpt-3.5-turbo":        "ChatGPT-16k",
			"gpt-4":                "GPT-4",
			"gpt-4o":               "GPT-4o",
			"gpt-4-vision-preview": "GPT-4-128k",
			"gpt-4-turbo-preview":  "Claude-3-Opus",
			"Claude-3.5-Sonnet":    "Claude-3.5-Sonnet",
			"Claude-3-Sonnet":      "Claude-3-Sonnet",
			"Claude-3-Haiku":       "Claude-3-Haiku",
			"Llama-3-70b-Groq":     "Llama-3-70b-Groq",
			"Gemini-1.5-Pro":       "Gemini-1.5-Pro",
			"Gemini-1.5-Pro-128k":  "Gemini-1.5-Pro-128k",
			"Gemini-1.5-Pro-1M":    "Gemini-1.5-Pro-1M",
			"DALL-E-3":             "DALL-E-3",
			"StableDiffusionXL":    "StableDiffusionXL",
		}
	}

	Models.Object = ""

	for key := range Conf.Bot {
		Models.Data = append(Models.Data, ModelDef{
			ID:      key,
			Object:  "",
			Created: 0,
			OwnedBy: "",
		})
	}
}
