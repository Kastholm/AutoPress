import os
import base64
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI
#TODO Hvis artikler omhandler nogen specifikke ting, bed ChatGPT om returnere en tom artikel []
instructions = """
Du er en erfaren dansk journalist.  
Omskriv artiklen fuldstændigt med ny vinkel, ny struktur og i andre ord, men behold fakta.  
Teksten skal:  
- Være på dansk.  
- Minimum 500 ord.  
- Have en fængende titel og teaser, der giver læseren lyst til at klikke.  
- Ikke starte artiklen med "I en...".  
- Indeholde maks. 2 citater (citater må ikke omskrives).  
- Være skrevet i journalistisk stil: objektiv, letlæselig, aktivt sprog.  
- Undgå gentagelser og fyldord.
- Byg artiklen op med tydelig rubrik (title), kort teaser og indhold i HTML-format klar til WordPress.
- Tildel en meningsfuld kategori blandt Nyheder, Udland, 112(omhanlder politisager i Danmark), Sundhed, hvis ingen kategorier 
  passer til artiklen, tildel en anden passende kategori.
- Tildel mellem 1 og 3 relevante og fyldige tags til denne tekst med stort forbogstav. Anvend ikke niche tags men kun meget brede tags som fx Trafik, Færdselsregler, Medicin, Sociale Medier, osv.
- Returnér resultatet i følgende JSON-struktur, kun objektet, intet andet:

{
  "id": Artiklens oprindelig ID,
  "title": "Artiklens titel",
  "teaser": "Artiklens teaser",
  "content": "<p>Artiklens indhold i HTML</p>",
  "image_url": "eksisterende img url",
  "categories": "Artiklens kategori",
  "categories_desc": "Kategori beskrivelse",
  "tags: "Artiklens tags",
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

    def send_prompt(self, prompt, log, instructions=instructions, version='gpt-5-mini'):
        if self.client:
            try:
                response = self.client.responses.create(
                    model=version,
                    instructions=instructions,
                    input=f'{prompt}',
                )
                response = response.output_text
                log(f' 🔍 Prompt Success: {response}', 'h2')
            except Exception as e:
                log(f"Prompt Error: {e}", 'h2')
        else:
            response = ''
            log("No client available", 'h2')
        
        return response

    def generate_img(self, title, img, log):

        if self.client:
            try:
                log(f' 🔍 AI Generating image for post {title}', 'h2')
                img_content = requests.get(img)
                content_type = img_content.headers.get("Content-Type")
                img_data = requests.get(img).content
                img_base64 = base64.b64encode(img_data).decode("utf-8")
                
                response = self.client.responses.create(
                    model='gpt-4.1',
                    input=[
                        {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": f""" 
                            Tag dette vedhæftede billede og lav det 40% om. Så det ligner originalen, men har en lille variation.
                            Det skal størrelsesmæssigt passe til en artikel.
                            Hvis billedet indeholder et logo eller varemærke må selve dette ikke ændres, så skal ting som baggrunden eller andre detaljer ændres for at skabe variation.
                            """},
                            {
                                "type": "input_image",
                                "image_url": f'data:{content_type};base64,{img_base64}'
                            }
                        ],
                      }
                    ],
                    tools=[{"type": "image_generation", "quality": "high"}],
                )
                image_generation_calls = [
                    output
                    for output in response.output
                    if output.type == "image_generation_call"
                ]

                image_data = [output.result for output in image_generation_calls]

                if image_data:
                    image_base64 = image_data[0]
                    log(f' ✅ Success AI Generated image for post {title}', 'h2')
                    #with open("gift-basket.webp", "wb") as f:
                    #    f.write(base64.b64decode(image_base64))
                    
                    image_bytes = base64.b64decode(image_base64)

                    pil_image = Image.open(BytesIO(image_bytes))

                    output = BytesIO()
                    pil_image.save(output, format="WEBP", quality=80)
                    webp_bytes = output.getvalue()

                    return webp_bytes

                else:
                    log(f' ❌ Error AI Generated image for post {title}', 'h2')
            except Exception as e:
                log(f' ❌ Reason Error AI Generated image for post {e}', 'h2')
                
        return None