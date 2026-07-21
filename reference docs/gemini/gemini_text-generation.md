> [!NOTE]
> **Note:** This version of the page covers the previous **generateContent API** . We recommend using the new [Interactions API](https://ai.google.dev/gemini-api/docs/interactions-overview) for access to all the latest features and models. You can use the toggle on this page to switch to the [Interactions API version of this page](https://ai.google.dev/gemini-api/docs/text-generation).

The Gemini API can generate text output from text, images, video, and audio
inputs.

Here's a basic example:

### Python

    from google import genai

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents="How does AI work?"
    )
    print(response.text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: "How does AI work?",
      });
      console.log(response.text);
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      result, _ := client.Models.GenerateContent(
          ctx,
          "gemini-3.5-flash",
          genai.Text("Explain how AI works in a few words"),
          nil,
      )

      fmt.Println(result.Text())
    }

### Java

    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentResponse;

    public class GenerateContentWithTextInput {
      public static void main(String[] args) {

        Client client = new Client();

        GenerateContentResponse response =
            client.models.generateContent("gemini-3.5-flash", "How does AI work?", null);

        System.out.println(response.text());
      }
    }

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "How does AI work?"
              }
            ]
          }
        ]
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const payload = {
        contents: [
          {
            parts: [
              { text: 'How AI does work?' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

## Thinking with Gemini

Gemini models often have ["thinking"](https://ai.google.dev/gemini-api/docs/thinking) enabled by default
which allows the model to reason before responding to a request.

Each model supports different thinking configurations which gives you control
over cost, latency, and intelligence. For more details, see the
[thinking guide](https://ai.google.dev/gemini-api/docs/thinking#set-budget).

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents="How does AI work?",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low")
        ),
    )
    print(response.text)

### JavaScript

    import { GoogleGenAI, ThinkingLevel } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: "How does AI work?",
        config: {
          thinkingConfig: {
            thinkingLevel: ThinkingLevel.LOW,
          },
        }
      });
      console.log(response.text);
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      thinkingLevelVal := "low"

      result, _ := client.Models.GenerateContent(
          ctx,
          "gemini-3.5-flash",
          genai.Text("How does AI work?"),
          &genai.GenerateContentConfig{
            ThinkingConfig: &genai.ThinkingConfig{
                ThinkingLevel: &thinkingLevelVal,
            },
          }
      )

      fmt.Println(result.Text())
    }

### Java

    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentConfig;
    import com.google.genai.types.GenerateContentResponse;
    import com.google.genai.types.ThinkingConfig;
    import com.google.genai.types.ThinkingLevel;

    public class GenerateContentWithThinkingConfig {
      public static void main(String[] args) {

        Client client = new Client();

        GenerateContentConfig config =
            GenerateContentConfig.builder()
                .thinkingConfig(ThinkingConfig.builder().thinkingLevel(new ThinkingLevel("low")))
                .build();

        GenerateContentResponse response =
            client.models.generateContent("gemini-3.5-flash", "How does AI work?", config);

        System.out.println(response.text());
      }
    }

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "How does AI work?"
              }
            ]
          }
        ],
        "generationConfig": {
          "thinkingConfig": {
            "thinkingLevel": "low"
          }
        }
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const payload = {
        contents: [
          {
            parts: [
              { text: 'How AI does work?' },
            ],
          },
        ],
        generationConfig: {
          thinkingConfig: {
            thinkingLevel: 'low'
          }
        }
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

## System instructions and other configurations

You can guide the behavior of Gemini models with system instructions. To do so,
pass a [`GenerateContentConfig`](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig)
object.

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="You are a cat. Your name is Neko."),
        contents="Hello there"
    )

    print(response.text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: "Hello there",
        config: {
          systemInstruction: "You are a cat. Your name is Neko.",
        },
      });
      console.log(response.text);
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      config := &genai.GenerateContentConfig{
          SystemInstruction: genai.NewContentFromText("You are a cat. Your name is Neko.", genai.RoleUser),
      }

      result, _ := client.Models.GenerateContent(
          ctx,
          "gemini-3.5-flash",
          genai.Text("Hello there"),
          config,
      )

      fmt.Println(result.Text())
    }

### Java

    import com.google.genai.Client;
    import com.google.genai.types.Content;
    import com.google.genai.types.GenerateContentConfig;
    import com.google.genai.types.GenerateContentResponse;
    import com.google.genai.types.Part;

    public class GenerateContentWithSystemInstruction {
      public static void main(String[] args) {

        Client client = new Client();

        GenerateContentConfig config =
            GenerateContentConfig.builder()
                .systemInstruction(
                    Content.fromParts(Part.fromText("You are a cat. Your name is Neko.")))
                .build();

        GenerateContentResponse response =
            client.models.generateContent("gemini-3.5-flash", "Hello there", config);

        System.out.println(response.text());
      }
    }

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -d '{
        "system_instruction": {
          "parts": [
            {
              "text": "You are a cat. Your name is Neko."
            }
          ]
        },
        "contents": [
          {
            "parts": [
              {
                "text": "Hello there"
              }
            ]
          }
        ]
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const systemInstruction = {
        parts: [{
          text: 'You are a cat. Your name is Neko.'
        }]
      };

      const payload = {
        systemInstruction,
        contents: [
          {
            parts: [
              { text: 'Hello there' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

The [`GenerateContentConfig`](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig)
object also lets you override default generation parameters, such as
[`max_output_tokens`](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig).

> [!NOTE]
> The \`temperature\`, \`top_p\`, and \`top_k\` parameters control how the model generates responses. Although you can modify these parameters, we strongly recommend keeping them at their default values for Gemini 3.x models. Changing these parameters (for example, setting the temperature below 1.0) can cause unexpected behavior, such as looping or degraded performance, particularly in complex mathematical or reasoning tasks.

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=["Explain how AI works"],
        config=types.GenerateContentConfig(
            max_output_tokens=1000
        )
    )
    print(response.text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: "Explain how AI works",
        config: {
          maxOutputTokens: 1000,
        },
      });
      console.log(response.text);
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "log"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      config := &genai.GenerateContentConfig{
        MaxOutputTokens:   1000,
        ResponseMIMEType:  "application/json",
      }

      result, _ := client.Models.GenerateContent(
        ctx,
        "gemini-3.5-flash",
        genai.Text("What is the average size of a swallow?"),
        config,
      )

      fmt.Println(result.Text())
    }

### Java

    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentConfig;
    import com.google.genai.types.GenerateContentResponse;

    public class GenerateContentWithConfig {
      public static void main(String[] args) {

        Client client = new Client();

        GenerateContentConfig config = GenerateContentConfig.builder().maxOutputTokens(1000).build();

        GenerateContentResponse response =
            client.models.generateContent("gemini-3.5-flash", "Explain how AI works", config);

        System.out.println(response.text());
      }
    }

### REST

    curl https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "Explain how AI works"
              }
            ]
          }
        ],
        "generationConfig": {
          "stopSequences": [
            "Title"
          ],
          "maxOutputTokens": 1000
        }
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const generationConfig = {
        maxOutputTokens: 1000,
        responseFormat: { text: { mimeType: "text/plain" } },
      };

      const payload = {
        generationConfig,
        contents: [
          {
            parts: [
              { text: 'Explain how AI works in a few words' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

Refer to the [`GenerateContentConfig`](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig)
in our API reference for a complete list of configurable parameters and their
descriptions.

## Multimodal inputs

The Gemini API supports multimodal inputs, allowing you to combine text with
media files. The following example demonstrates providing an image:

### Python

    from PIL import Image
    from google import genai

    client = genai.Client()

    image = Image.open("/path/to/organ.png")
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[image, "Tell me about this instrument"]
    )
    print(response.text)

### JavaScript

    import {
      GoogleGenAI,
      createUserContent,
      createPartFromUri,
    } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const image = await ai.files.upload({
        file: "/path/to/organ.png",
      });
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: [
          createUserContent([
            "Tell me about this instrument",
            createPartFromUri(image.uri, image.mimeType),
          ]),
        ],
      });
      console.log(response.text);
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      imagePath := "/path/to/organ.jpg"
      imgData, _ := os.ReadFile(imagePath)

      parts := []*genai.Part{
          genai.NewPartFromText("Tell me about this instrument"),
          &genai.Part{
              InlineData: &genai.Blob{
                  MIMEType: "image/jpeg",
                  Data:     imgData,
              },
          },
      }

      contents := []*genai.Content{
          genai.NewContentFromParts(parts, genai.RoleUser),
      }

      result, _ := client.Models.GenerateContent(
          ctx,
          "gemini-3.5-flash",
          contents,
          nil,
      )

      fmt.Println(result.Text())
    }

### Java

    import com.google.genai.Client;
    import com.google.genai.Content;
    import com.google.genai.types.GenerateContentResponse;
    import com.google.genai.types.Part;

    public class GenerateContentWithMultiModalInputs {
      public static void main(String[] args) {

        Client client = new Client();

        Content content =
          Content.fromParts(
              Part.fromText("Tell me about this instrument"),
              Part.fromUri("/path/to/organ.jpg", "image/jpeg"));

        GenerateContentResponse response =
            client.models.generateContent("gemini-3.5-flash", content, null);

        System.out.println(response.text());
      }
    }

### REST

    # Use a temporary file to hold the base64 encoded image data
    TEMP_B64=$(mktemp)
    trap 'rm -f "$TEMP_B64"' EXIT
    base64 $B64FLAGS $IMG_PATH > "$TEMP_B64"

    # Use a temporary file to hold the JSON payload
    TEMP_JSON=$(mktemp)
    trap 'rm -f "$TEMP_JSON"' EXIT

    cat > "$TEMP_JSON" << EOF
    {
      "contents": [
        {
          "parts": [
            {
              "text": "Tell me about this instrument"
            },
            {
              "inline_data": {
                "mime_type": "image/jpeg",
                "data": "$(cat "$TEMP_B64")"
              }
            }
          ]
        }
      ]
    }
    EOF

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d "@$TEMP_JSON"

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const imageUrl = 'https://example.com/image.jpg';
      const image = getImageData(imageUrl);
      const payload = {
        contents: [
          {
            parts: [
              { image },
              { text: 'Tell me about this instrument' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

    function getImageData(url) {
      const blob = UrlFetchApp.fetch(url).getBlob();

      return {
        mimeType: blob.getContentType(),
        data: Utilities.base64Encode(blob.getBytes())
      };
    }

For alternative methods of providing images and more advanced image processing,
see our [image understanding guide](https://ai.google.dev/gemini-api/docs/image-understanding).
The API also supports [document](https://ai.google.dev/gemini-api/docs/document-processing), [video](https://ai.google.dev/gemini-api/docs/video-understanding), and [audio](https://ai.google.dev/gemini-api/docs/audio)
inputs and understanding.

## Streaming responses

By default, the model returns a response only after the entire generation
process is complete.

For more fluid interactions, use streaming to receive [`GenerateContentResponse`](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse) instances incrementally
as they're generated.

### Python

    from google import genai

    client = genai.Client()

    response = client.models.generate_content_stream(
        model="gemini-3.5-flash",
        contents=["Explain how AI works"]
    )
    for chunk in response:
        print(chunk.text, end="")

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContentStream({
        model: "gemini-3.5-flash",
        contents: "Explain how AI works",
      });

      for await (const chunk of response) {
        console.log(chunk.text);
      }
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      stream := client.Models.GenerateContentStream(
          ctx,
          "gemini-3.5-flash",
          genai.Text("Write a story about a magic backpack."),
          nil,
      )

      for chunk, _ := range stream {
          part := chunk.Candidates[0].Content.Parts[0]
          fmt.Print(part.Text)
      }
    }

### Java

    import com.google.genai.Client;
    import com.google.genai.ResponseStream;
    import com.google.genai.types.GenerateContentResponse;

    public class GenerateContentStream {
      public static void main(String[] args) {

        Client client = new Client();

        ResponseStream<GenerateContentResponse> responseStream =
          client.models.generateContentStream(
              "gemini-3.5-flash", "Write a story about a magic backpack.", null);

        for (GenerateContentResponse res : responseStream) {
          System.out.print(res.text());
        }

        // To save resources and avoid connection leaks, it is recommended to close the response
        // stream after consumption (or using try block to get the response stream).
        responseStream.close();
      }
    }

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:streamGenerateContent?alt=sse" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      --no-buffer \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "Explain how AI works"
              }
            ]
          }
        ]
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const payload = {
        contents: [
          {
            parts: [
              { text: 'Explain how AI works' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:streamGenerateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

## Multi-turn conversations (chat)

Our SDKs provide functionality to collect multiple rounds of prompts and
responses into a chat, giving you an easy way to keep track of the conversation
history.

> [!NOTE]
> **Note:** Chat functionality is only implemented as part of the SDKs. Behind the scenes, it still uses the [`generateContent`](https://ai.google.dev/api/generate-content#method:-models.generatecontent) API. For multi-turn conversations, the full conversation history is sent to the model with each follow-up turn.

### Python

    from google import genai

    client = genai.Client()
    chat = client.chats.create(model="gemini-3.5-flash")

    response = chat.send_message("I have 2 dogs in my house.")
    print(response.text)

    response = chat.send_message("How many paws are in my house?")
    print(response.text)

    for message in chat.get_history():
        print(f'role - {message.role}',end=": ")
        print(message.parts[0].text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const chat = ai.chats.create({
        model: "gemini-3.5-flash",
        history: [
          {
            role: "user",
            parts: [{ text: "Hello" }],
          },
          {
            role: "model",
            parts: [{ text: "Great to meet you. What would you like to know?" }],
          },
        ],
      });

      const response1 = await chat.sendMessage({
        message: "I have 2 dogs in my house.",
      });
      console.log("Chat response 1:", response1.text);

      const response2 = await chat.sendMessage({
        message: "How many paws are in my house?",
      });
      console.log("Chat response 2:", response2.text);
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      history := []*genai.Content{
          genai.NewContentFromText("Hi nice to meet you! I have 2 dogs in my house.", genai.RoleUser),
          genai.NewContentFromText("Great to meet you. What would you like to know?", genai.RoleModel),
      }

      chat, _ := client.Chats.Create(ctx, "gemini-3.5-flash", nil, history)
      res, _ := chat.SendMessage(ctx, genai.Part{Text: "How many paws are in my house?"})

      if len(res.Candidates) > 0 {
          fmt.Println(res.Candidates[0].Content.Parts[0].Text)
      }
    }

### Java

    import com.google.genai.Chat;
    import com.google.genai.Client;
    import com.google.genai.types.Content;
    import com.google.genai.types.GenerateContentResponse;

    public class MultiTurnConversation {
      public static void main(String[] args) {

        Client client = new Client();
        Chat chatSession = client.chats.create("gemini-3.5-flash");

        GenerateContentResponse response =
            chatSession.sendMessage("I have 2 dogs in my house.");
        System.out.println("First response: " + response.text());

        response = chatSession.sendMessage("How many paws are in my house?");
        System.out.println("Second response: " + response.text());

        // Get the history of the chat session.
        // Passing 'true' to getHistory() returns the curated history, which excludes
        // empty or invalid parts.
        // Passing 'false' here would return the comprehensive history, including
        // empty or invalid parts.
        ImmutableList<Content> history = chatSession.getHistory(true);
        System.out.println("History: " + history);
      }
    }

### REST

    curl https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "role": "user",
            "parts": [
              {
                "text": "Hello"
              }
            ]
          },
          {
            "role": "model",
            "parts": [
              {
                "text": "Great to meet you. What would you like to know?"
              }
            ]
          },
          {
            "role": "user",
            "parts": [
              {
                "text": "I have two dogs in my house. How many paws are in my house?"
              }
            ]
          }
        ]
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const payload = {
        contents: [
          {
            role: 'user',
            parts: [
              { text: 'Hello' },
            ],
          },
          {
            role: 'model',
            parts: [
              { text: 'Great to meet you. What would you like to know?' },
            ],
          },
          {
            role: 'user',
            parts: [
              { text: 'I have two dogs in my house. How many paws are in my house?' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

Streaming can also be used for multi-turn conversations.

### Python

    from google import genai

    client = genai.Client()
    chat = client.chats.create(model="gemini-3.5-flash")

    response = chat.send_message_stream("I have 2 dogs in my house.")
    for chunk in response:
        print(chunk.text, end="")

    response = chat.send_message_stream("How many paws are in my house?")
    for chunk in response:
        print(chunk.text, end="")

    for message in chat.get_history():
        print(f'role - {message.role}', end=": ")
        print(message.parts[0].text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const chat = ai.chats.create({
        model: "gemini-3.5-flash",
        history: [
          {
            role: "user",
            parts: [{ text: "Hello" }],
          },
          {
            role: "model",
            parts: [{ text: "Great to meet you. What would you like to know?" }],
          },
        ],
      });

      const stream1 = await chat.sendMessageStream({
        message: "I have 2 dogs in my house.",
      });
      for await (const chunk of stream1) {
        console.log(chunk.text);
        console.log("_".repeat(80));
      }

      const stream2 = await chat.sendMessageStream({
        message: "How many paws are in my house?",
      });
      for await (const chunk of stream2) {
        console.log(chunk.text);
        console.log("_".repeat(80));
      }
    }

    await main();

### Go

    package main

    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )

    func main() {

      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }

      history := []*genai.Content{
          genai.NewContentFromText("Hi nice to meet you! I have 2 dogs in my house.", genai.RoleUser),
          genai.NewContentFromText("Great to meet you. What would you like to know?", genai.RoleModel),
      }

      chat, _ := client.Chats.Create(ctx, "gemini-3.5-flash", nil, history)
      stream := chat.SendMessageStream(ctx, genai.Part{Text: "How many paws are in my house?"})

      for chunk, _ := range stream {
          part := chunk.Candidates[0].Content.Parts[0]
          fmt.Print(part.Text)
      }
    }

### Java

    import com.google.genai.Chat;
    import com.google.genai.Client;
    import com.google.genai.ResponseStream;
    import com.google.genai.types.GenerateContentResponse;

    public class MultiTurnConversationWithStreaming {
      public static void main(String[] args) {

        Client client = new Client();
        Chat chatSession = client.chats.create("gemini-3.5-flash");

        ResponseStream<GenerateContentResponse> responseStream =
            chatSession.sendMessageStream("I have 2 dogs in my house.", null);

        for (GenerateContentResponse response : responseStream) {
          System.out.print(response.text());
        }

        responseStream = chatSession.sendMessageStream("How many paws are in my house?", null);

        for (GenerateContentResponse response : responseStream) {
          System.out.print(response.text());
        }

        // Get the history of the chat session. History is added after the stream
        // is consumed and includes the aggregated response from the stream.
        System.out.println("History: " + chatSession.getHistory(false));
      }
    }

### REST

    curl https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:streamGenerateContent?alt=sse \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "role": "user",
            "parts": [
              {
                "text": "Hello"
              }
            ]
          },
          {
            "role": "model",
            "parts": [
              {
                "text": "Great to meet you. What would you like to know?"
              }
            ]
          },
          {
            "role": "user",
            "parts": [
              {
                "text": "I have two dogs in my house. How many paws are in my house?"
              }
            ]
          }
        ]
      }'

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');

    function main() {
      const payload = {
        contents: [
          {
            role: 'user',
            parts: [
              { text: 'Hello' },
            ],
          },
          {
            role: 'model',
            parts: [
              { text: 'Great to meet you. What would you like to know?' },
            ],
          },
          {
            role: 'user',
            parts: [
              { text: 'I have two dogs in my house. How many paws are in my house?' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:streamGenerateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

## Prompting tips

Consult our [prompt engineering guide](https://ai.google.dev/gemini/docs/prompting-strategies) for
suggestions on getting the most out of Gemini.

## What's next

- Try [Gemini in Google AI Studio](https://aistudio.google.com).
- Experiment with [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) for JSON-like responses.
- Explore Gemini's [image](https://ai.google.dev/gemini-api/docs/image-understanding), [video](https://ai.google.dev/gemini-api/docs/video-understanding), [audio](https://ai.google.dev/gemini-api/docs/audio) and [document](https://ai.google.dev/gemini-api/docs/document-processing) understanding capabilities.
- Learn about multimodal [file prompting strategies](https://ai.google.dev/gemini-api/docs/files#prompt-guide).

## Content generation

This is the central endpoint for sending prompts to the model. There are two
endpoints for generating content, the key difference is how you receive the
response:

- **[`generateContent`](https://ai.google.dev/api/generate-content#method:-models.generatecontent)
  (REST)**: Receives a request and provides a single response after the model has finished its entire generation.
- **[`streamGenerateContent`](https://ai.google.dev/api/generate-content#method:-models.streamgeneratecontent)
  (SSE)**: Receives the exact same request, but the model streams back chunks of the response as they are generated. This provides a better user experience for interactive applications as it lets you display partial results immediately.

### Request body structure

The [request body](https://ai.google.dev/api/generate-content#request-body) is a JSON object that is
**identical** for both standard and streaming modes and is built from a few core
objects:

- [`Content`](https://ai.google.dev/api/caching#Content) object: Represents a single turn in a conversation.
- [`Part`](https://ai.google.dev/api/caching#Part) object: A piece of data within a `Content` turn (like text or an image).
- `inline_data` ([`Blob`](https://ai.google.dev/api/caching#Blob)): A container for raw media bytes and their MIME type.

At the highest level, the request body contains a `contents` object, which is a
list of `Content` objects, each representing turns in conversation. In most
cases, for basic text generation, you will have a single `Content` object, but
if you'd like to maintain conversation history, you can use multiple `Content`
objects.

The following shows a typical `generateContent` request body:

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
              "role": "user",
              "parts": [
                  // A list of Part objects goes here
              ]
          },
          {
              "role": "model",
              "parts": [
                  // A list of Part objects goes here
              ]
          }
        ]
      }'

### Response body structure

The [response body](https://ai.google.dev/api/generate-content#response-body) is similar for both
the streaming and standard modes except for the following:

- Standard mode: The response body contains an instance of [`GenerateContentResponse`](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse).
- Streaming mode: The response body contains a stream of [`GenerateContentResponse`](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse) instances.

At a high level, the response body contains a `candidates` object, which is a
list of `Candidate` objects. The `Candidate` object contains a `Content`
object that has the generated response returned from the model.

## REST API Examples

### Multimodal prompt (text and image)

To provide both text and an image in a prompt, the `parts` array should contain
two `Part` objects: one for the text, and one for the image `inline_data`.

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d '{
        "contents": [{
        "parts":[
            {
                "inline_data": {
                "mime_type":"image/jpeg",
                "data": "/9j/4AAQSkZJRgABAQ... (base64-encoded image)"
                }
            },
            {"text": "What is in this picture?"},
          ]
        }]
      }'

### Multi-turn conversations (chat)

To build a conversation with multiple turns, you define the `contents` array
with multiple `Content` objects. The API will use this entire history as context
for the next response. The `role` for each `Content` object should alternate
between `user` and `model`.

> [!NOTE]
> **Note:** The client SDKs provide a chat interface that manages this list for you automatically. When using the REST API, you are responsible for maintaining the conversation history.

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "role": "user",
            "parts": [
              { "text": "Hello." }
            ]
          },
          {
            "role": "model",
            "parts": [
              { "text": "Hello! How can I help you today?" }
            ]
          },
          {
            "role": "user",
            "parts": [
              { "text": "Please write a four-line poem about the ocean." }
            ]
          }
        ]
      }'

### Key takeaways

- `Content` is the envelope: It's the top-level container for a message turn, whether it's from the user or the model.
- `Part` enables multimodality: Use multiple `Part` objects within a single `Content` object to combine different types of data (text, image, video URI, etc.).
- Choose your data method:
  - For small, directly embedded media (like most images), use a `Part` with `inline_data`.
  - For larger files or files you want to reuse across requests, use the File API to upload the file and reference it with a `file_data` part.
- Manage conversation history: For chat applications using the REST API, build the `contents` array by appending `Content` objects for each turn, alternating between `"user"` and `"model"` roles. If you're using an SDK, refer to the SDK documentation for the recommended way to manage conversation history.

## Response examples

The following examples show how these components come together for different
types of requests.

### Text-only response

A default text response consists of a `candidates` array with one or more
`content` objects that contain the model's response.

The following is an example of a **standard** response:

    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": "At its core, Artificial Intelligence works by learning from vast amounts of data ..."
              }
            ],
            "role": "model"
          },
          "finishReason": "STOP",
          "index": 1
        }
      ],
    }

The following is series of **streaming** responses. Each response contains a
`responseId` that ties the full response together:

    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": "The image displays"
              }
            ],
            "role": "model"
          },
          "index": 0
        }
      ],
      "usageMetadata": {
        "promptTokenCount": ...
      },
      "modelVersion": "gemini-3.5-flash",
      "responseId": "mAitaLmkHPPlz7IPvtfUqQ4"
    }

    ...

    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": " the following materials:\n\n*   **Wood:** The accordion and the violin are primarily"
              }
            ],
            "role": "model"
          },
          "index": 0
        }
      ],
      "usageMetadata": {
        "promptTokenCount": ...
      }
      "modelVersion": "gemini-3.5-flash",
      "responseId": "mAitaLmkHPPlz7IPvtfUqQ4"
    }

## Live API (BidiGenerateContent) WebSockets API

Live API offers a stateful WebSocket based API for bi-directional streaming to
enable real-time streaming use cases. You can review
[Live API guide](https://ai.google.dev/gemini-api/docs/live) and the [Live API reference](https://ai.google.dev/api/live)
for more details.

## Specialized models

In addition to the Gemini family of models, Gemini API offers endpoints for
specialized models such as [Imagen](https://ai.google.dev/gemini-api/docs/imagen),
[Lyria](https://ai.google.dev/gemini-api/docs/music-generation) and
[embedding](https://ai.google.dev/gemini-api/docs/embeddings) models. You can check out
these guides under the Models section.

## Platform APIs

The rest of the endpoints enable additional capabilities to use with the main
endpoints described so far. Check out topics
[Batch mode](https://ai.google.dev/gemini-api/docs/batch-mode) and
[File API](https://ai.google.dev/gemini-api/docs/files) in the Guides section to learn more.

## What's next

If you're just getting started, check out the following guides, which will help
you understand the Gemini API programming model:

- [Gemini API Get started guide](https://ai.google.dev/gemini-api/docs/generate-content/get-started)
- [Gemini model guide](https://ai.google.dev/gemini-api/docs/models/gemini)

You might also want to check out the capabilities guides, which introduce different
Gemini API features and provide code examples:

- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [Context caching](https://ai.google.dev/gemini-api/docs/caching)
- [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)