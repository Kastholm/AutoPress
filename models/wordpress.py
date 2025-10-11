import os
import requests
import base64
import json
from io import BytesIO
from PIL import Image
from slugify import slugify
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

class WordPress:

    def __init__(self):
        load_dotenv()
        self.credentials = {
            'user': os.getenv('WP_USERNAME'),
            'pass': os.getenv('WP_APP_PW'),
            'site': os.getenv('WP_PATH')
        }
        self.endpoint = f'https://{self.credentials["site"]}/wp-json/wp/v2/posts'

        if not self.credentials['pass']:
            print('credentials not set')

        


    def connect_to_wordpress(self, path):
        url = f'https://{self.credentials["site"]}/wp-json/wp/v2/{path}/?per_page=100&&context=edit'
        s = requests.Session()
        s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
        response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))

        if response.status_code == 200:
            print(f'✅ AUTH Connection to new site {self.credentials["site"]}/{path} sucess')
        else:
            print(f'⛔ AUTH Connection to new site {self.credentials["site"]}/{path} failed: {response.status_code}, {response.text}')
            return

        return url, response.json()


    def apply_category(self, new_article):
        if new_article['categories']:
            category_id = ''
            fetch_url, fetched_categories = self.connect_to_wordpress('categories')
            
            for fetched_category in fetched_categories:
                if fetched_category['name'] == new_article['categories']:
                    print('Category in use')
                    category_id = fetched_category['id']
                    break
            #If category_id is empy it indicates that no categories was found in the db
            if category_id == '':
                category = ({
                        "name": new_article['categories'],
                        "slug": slugify(new_article['categories']),
                        "description": new_article['categories_desc'],
                        "parent": 0
                        })
                r = requests.post(
                    fetch_url,
                    json=category,
                    auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                    headers={"Content-Type": "application/json"}
                )
                if r.status_code == 201:
                    category_json = r.json()
                    print(category_json)
                    category_id = category_json['id']
                    print('New Category created')
                else:
                    print('Category request post failed ❌')
            
            return category_id


    def apply_tags(self, new_article):
        print('🟢⛔', new_article, 'TAGS')
        if new_article['tags']:
            apply_tag_ids_arr = []
            fetched_fuzzy_tags_arr = []
            fetch_url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags/?per_page=100&&context=edit'
            tags = [t.strip() for t in new_article['tags']] if isinstance(new_article['tags'], list) else [t.strip() for t in new_article['tags'].split(',')]
            for tag in tags:
                #See if article tags exist in the database, if so apply tags to array.
                url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags?slug={slugify(tag)}'
                s = requests.Session()
                s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
                tag_response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))
                tag_response_json = tag_response.json()
                #If no tags are found, create them
                if tag_response_json == []:
                    tag = ({
                            "name": tag,
                            "slug": slugify(tag),
                            "description": ''
                            })
                    r = requests.post(
                        fetch_url,
                        json=tag,
                        auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                        headers={"Content-Type": "application/json"}
                    )
                    if r.status_code == 201:
                        print('tag data posted')
                        tag_json = r.json()
                        apply_tag_ids_arr.append(tag_json['id'])
                    else:
                        print('tag data failed request ❌')
                else:
                    apply_tag_ids_arr.append(tag_response_json[0]['id'])

            return apply_tag_ids_arr

    def upload_and_convert_img(self, new_article, webp_bytes, caption):
        
        lib_url = f'https://{self.credentials["site"]}/wp-json/wp/v2/media'

        filename = f"{slugify(new_article['image_title'])}.webp"
        
        r = requests.post(
            lib_url,
            files={'file': (filename, webp_bytes, 'image/webp')},
            auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
        
        print(f'Image upload status: {r.status_code}')
        print(f'Image upload response: {r.text}')
        
        if r.status_code == 201:
            data = r.json()
            print(data, 'IMAGE DATA REQUESTED')
            
            media_id = data["id"]
            print('ID', media_id)
            
            # Update image metadata
            update_response = requests.post(
                f"{lib_url}/{media_id}",
                json={"alt_text": new_article['image_desc'], "caption": caption},
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )
            print(f'Image metadata update status: {update_response.status_code}')
            
            return media_id
        else:
            print(f'❌ Image upload failed: {r.status_code}, {r.text}')
            return None


    def image_decision(self, open_ai, new_article):
        image_webp = ''
        image_library_id = ''
        print(new_article, '🟢🟢')

        #Investigate if the image has no License and therefore can be used.
        prompt=f"Billedets caption = {new_article['image_caption']}"
        instructions=f"""
        Ud fra denne caption skal du vurdere om billedet er licensfrit.
        Alle billeder fra TikTok, Facebook, Instagram, youtube, Google Maps osv er skærmbilleder, derfor er de godkendte og licensfrie.
        Såvel som billeder fra gratis sites som Pexels, Pixabay, Unsplash og andre du kender.

        Alt i alt, skal du vurdere om dette billede er licensfrit og om vi kan benytte det til vores artikel.

        Det originale billede kan du se her hvis det hjælper dig med din vurdering:
        {new_article['media']}

        Vi skal bruge et dansk søgeord ud fra titlen {new_article['image_title']}.
        F.eks hvis titlen er 'Edderkop kravler hen af gulvet' skal søgeordet bare være Edderkop.
        Hvis artiklen omhandler en privatperson hvor billedegenerering ikke er tilladt, som fx 'Jonas Vingegaard',
        skal søgeordet være noget som fx 'Cykelrytter', 'Tour de France'. 

        Du skal returnere i dette JSON format ud fra om det er licensfrit eller ikke.
        False = Ikke Licensfrit
        True = Licensfrit

        {{
            "License": bool,
            "Reason": string,
            "Searchword": string
        }}
        """

        whitelist_response = open_ai.send_prompt(prompt, instructions, version='gpt-5-nano')
        ai_whitelist_response = json.loads(whitelist_response)
        print(ai_whitelist_response)
        #Convert the none licensed image to webp and return it
        if ai_whitelist_response['License']:
            img = Image.open(BytesIO(requests.get(new_article['media']).content))
            output = BytesIO()
            img.convert("RGB").save(output, format="WEBP", quality=80)
            image_webp_bytes = output.getvalue()
            img_id = self.upload_and_convert_img(new_article, image_webp_bytes, new_article['image_caption'])
            return img_id
        else:
            #If no licensed image is found, search the database for a matching image
            url = f"https://{self.credentials['site']}/wp-json/wp/v2/media?search={slugify(ai_whitelist_response['Searchword'])}"
            print('Searching for images with searchword: ', slugify(ai_whitelist_response['Searchword']))
            resp_images = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))
            resp_images_json = resp_images.json()
            if resp_images_json:
                fetched_imgs = []
                for img in resp_images_json:
                    img_data = ({
                        "id": img['id'],
                        "title": img['title']['rendered'],
                        "desc": img['alt_text']
                    })
                    fetched_imgs.append(img_data)
                print(fetched_imgs, 'FETCHED IMGS')
                prompt = f'JSON liste med billeder ud fra søgeord: {fetched_imgs}'
                instructions= f""" 
                Du får en liste af billeder fra et wordpress bibliotek.
                Du skal vurdere om en af disse billeder vil passe til artiklen med titel {new_article['title']}.
                
                Hvis du mener en billerderne passer til artiklen.
                Fortæller du det i dette JSON format, som er det eneste du skal returnere.

                {{
                    "image_id": "tom hvis ingen valgt, ellers skriv image id fra JSON",
                    "reason": "kort forklaring hvis et billede er valgt"
                }} 
                """
                database_img_response = open_ai.send_prompt(prompt, instructions, version='gpt-5-nano')
                database_img_response_json = json.loads(database_img_response)
                print(database_img_response_json, 'DATABASE IMG RESPONSE JSON')
                #If an image is found, return it
                if database_img_response_json and database_img_response_json['image_id']:
                    img_id = database_img_response_json['image_id']
                    return img_id
                else:
                    print('No images found in database')

        #Generate an image with AI and return it as webp
        print('AI generating new image')
        image_webp_bytes = open_ai.generate_img(
            new_article['title'], new_article['media']
        )
        ##Upload the image to the database and return the id
        img_id = self.upload_and_convert_img(new_article, image_webp_bytes, 'AI Genereret')
        return img_id
                

    def publish_post(self, articles, img_id):
        if articles == []:
            print('No articles to WordPress')
            return

        for new_article in articles:
            print('🟢🟢 Publish post to WP 🟢🟢')

            #Connect og vælg cat,tag,jour
            category_id = self.apply_category(new_article)
            print(category_id, 'CATEGORY ID')
            tag_ids = self.apply_tags(new_article)
            print(tag_ids, 'TAG IDS')
            print(img_id, 'IMG ID')
            
            # Skip posting if image upload failed
            if img_id is None:
                print('❌ Skipping post due to failed image upload')
                continue

            
            #TODO tilvælg en random journalist

            ready_article = ({
                        "title": new_article['title'],
                        "content": new_article['content'],
                        "status": "publish",
                        'featured_media': img_id,
                        'categories': category_id,
                        'tags': tag_ids
            })

            r = requests.post(
                self.endpoint,
                json=ready_article,
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )

            print(ready_article,'⚔️')

            if r.status_code == 201:
                print(f'✅ AUTH Connection to new site {self.credentials["site"]} sucess')
            else:
                print(f'⛔ AUTH Connection to new site {self.credentials["site"]} failed: {r.status_code}, {r.text}')
            return
            r.raise_for_status()