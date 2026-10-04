# OpenAI

This file has miscellaneous information about the OpenAI API.  This 
information was helpful during the development of this project.

## Responses API

- sample definition of tools for the model

```json
[
    {
      "type": "function",
      "name": "add",
      "description": "Return the sum of two numbers."
      "strict": true,
      "parameters": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "a": {
            "type": "number",
            "description": "The first addend."
          },
          "b": {
            "type": "number",
            "description": "The second addend."
          }
        },
        "required": [
          "a",
          "b"
        ]
      },
    },
 ]
```