import os
from dotenv import load_dotenv
from openai import OpenAI

class ChatGPT:

    def __init__(self):
        load_dotenv()
        self.gpt_key = os.getenv("GPT_KEY")
        if self.gpt_key:
            self.client = OpenAI(
                api_key=self.gpt_key,
            )
        else:
            print("None or not usable API key provided")

    def send_prompt(self, prompt):
        if self.client:
            try:
                response = self.client.responses.create(
                    model='gpt-4o-mini',
                    instructions="You are awesome",
                    input="Say hi",
                )
                return response.output_text
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("No client available")


if __name__ == "__main__":

    test = ChatGPT()

    test.send_prompt("Hello")

