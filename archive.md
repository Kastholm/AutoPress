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