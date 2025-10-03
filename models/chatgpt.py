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
- Tildel en meningsfuld kategori blandt Nyheder, Udland, 112(omhanlder politisager i Danmark), Sundhed, hvis ingen kategorier 
  passer til artiklen, tildel en anden passende kategori.
- Tildel mellem 1 og 3 relevante og fyldige tags til denne tekst. Ignorér tags, der er for generelle eller for tynde.
- Returnér resultatet i følgende JSON-struktur, kun objektet, intet andet:

{
  "id": "Artiklens oprindelig ID",
  "title": "Artiklens titel",
  "teaser": "Artiklens teaser",
  "content": "<p>Artiklens indhold i HTML</p>",
  "image_url": "eksisterende img url",
  "categories": "Artiklens kategori",
  "categories_desc": "Kategori beskrivelse",
  "tags: "Artiklens tags"
}
"""

image_instructions = """
Generer et billede der ligner 98% det originale
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
        
        return response

    def generate_image(self, img):
        if self.client:
            try:
                response = self.client.responses.create(
                    model='gpt-4.1',
                    input=[
                        {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": f'{image_instructions}'},
                            {
                                "type": "input_image",
                                "image_url": f'{img}'
                            }
                        ],
                      }
                    ],
                    tools=[{"type": "image_generation"}],
                )
            except Exception as e:
                print(f"Error: {e}")
        else:
            response = ''
            print("No client available")
        print(response)
        return response