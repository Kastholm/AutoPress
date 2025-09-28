import os
from dotenv import load_dotenv
from openai import OpenAI

instructions = """
Du er en erfaren dansk journalist.  
Omskriv artiklen fuldstændigt med ny vinkel, ny struktur og i andre ord, men behold fakta.  
Teksten skal:  
- Være på dansk.  
- Maks. 500 ord.  
- Have en fængende titel og teaser, der giver læseren lyst til at klikke.  
- Ikke starte artiklen med "I en...".  
- Indeholde maks. 2 citater (citater må ikke omskrives).  
- Være skrevet i journalistisk stil: objektiv, letlæselig, aktivt sprog.  
- Undgå gentagelser og fyldord.  
- Byg artiklen op med tydelig rubrik (title), kort teaser og indhold i HTML-format klar til WordPress.  
- Returnér resultatet i følgende JSON-struktur:

artikel: {
  "id": "Artiklens oprindelig ID",
  "title": "Artiklens titel",
  "teaser": "Artiklens teaser",
  "content": "<p>Artiklens indhold i HTML</p>"
}
"""

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
                    instructions=instructions,
                    input=f'{prompt}',
                )
                response = response.output_text
            except Exception as e:
                print(f"Error: {e}")
        else:
            response = ''
            print("No client available")

        print(response)


        return response