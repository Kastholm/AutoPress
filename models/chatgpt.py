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
- Maks. 500 ord.  
- Have en fængende titel og teaser, der giver læseren lyst til at klikke.  
- Ikke starte artiklen med "I en...".  
- Indeholde maks. 2 citater (citater må ikke omskrives).  
- Være skrevet i journalistisk stil: objektiv, letlæselig, aktivt sprog.  
- Undgå gentagelser og fyldord.  
- Byg artiklen op med tydelig rubrik (title), kort teaser og indhold i HTML-format klar til WordPress.
- Tildel en meningsfuld kategori blandt Nyheder, Udland, 112(omhanlder politisager i Danmark), Sundhed, hvis ingen kategorier 
  passer til artiklen, tildel en anden passende kategori.
- Tildel mellem 1 og 3 relevante og fyldige tags til denne tekst. Anvend kun meget brede tags.
- Returnér resultatet i følgende JSON-struktur, kun objektet, intet andet:

{
  "id": "Artiklens oprindelig ID",
  "title": "Artiklens titel",
  "teaser": "Artiklens teaser",
  "content": "<p>Artiklens indhold i HTML</p>",
  "image_url": "eksisterende img url",
  "image_prompt": "Prompt til at generere et billede til artiklen",
  "image_title": "Titel det genererede billede",
  "image_desc": "Beskrivelse af hvad billedet indeholder",
  "categories": "Artiklens kategori",
  "categories_desc": "Kategori beskrivelse",
  "tags: "Artiklens tags",
  "image_searchword": "Et engelsk søgeord til Pexels, Unsplash API. Ord som 'Donald Trump', 'Supermarket', 'Boeing Airplane'"
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
        
        return response

    def generate_img(self, title, img):

        if self.client:
            try:
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
                    with open("gift-basket.webp", "wb") as f:
                        f.write(base64.b64decode(image_base64))
                    
                    image_bytes = base64.b64decode(image_base64)

                    pil_image = Image.open(BytesIO(image_bytes))

                    output = BytesIO()
                    pil_image.save(output, format="WEBP", quality=80)
                    webp_bytes = output.getvalue()

                    return webp_bytes

                else:
                    print(response.output.content)
            except Exception as e:
                print(e)
                
        return None

    def generate_img_two(self, title, img, prompt):
        r = requests.get(img)
        print(r.status_code, r.headers.get("Content-Type"))
        result = self.client.images.generate(
            model="gpt-image-1",
            prompt = f"""
            Skab et fotorealistisk billede, der passer til denne artikel med titel:
            {title}
            Ved hjælp af denne prompt:
            {prompt}

            Brug gerne det vedhæftede billede som reference for komposition, lys og stemning. 
            Det nye billede må gerne ligne det originale op til 90%.
            Link til originale billede: {img}

            Billedet skal have et bredt 16:9-format, egnet som artikel- eller hero-billede på et nyhedswebsite.
            
            Undgå al tekst, logoer og vandmærker på billedet.
            """
        )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        pil_image = Image.open(BytesIO(image_bytes))

        output = BytesIO()
        pil_image.save(output, format="WEBP", quality=80)
        webp_bytes = output.getvalue()

        return webp_bytes

    def generate_img_three(self, title, img):
        r = requests.get(img)
        print(r.status_code, r.headers.get("Content-Type"))
        buf = BytesIO(r.content); 
        buf.name = "source.jpg"
        f = self.client.files.create(file=buf, purpose="vision")

        response = self.client.responses.create(
            model="gpt-5",
            input = f"""
            Tag dette {img} og lav (40%) om. Så det ligner originalen, men har en lille variation
            """,
            tools=[{
                "type": "image_generation",
                "image_generation": {
                    "prompt": "Subtil variation af fotoet",
                    "referenced_image_ids": [f.id],
                    "size": "1024x1024",
                    "n": 1
                }
            }],
        )

        # Save the image to a file
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
            
        if image_data:
            image_base64 = image_data[0]
            image_bytes = base64.b64decode(image_base64)
            pil_image = Image.open(BytesIO(image_bytes))

            output = BytesIO()
            pil_image.save(output, format="WEBP", quality=80)
            webp_bytes = output.getvalue()

            with open("otter.png", "wb") as f:
                f.write(base64.b64decode(image_base64))
            return webp_bytes
        
        return None