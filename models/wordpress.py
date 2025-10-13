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

        


    def connect_to_wordpress(self, path, log):
        url = f'https://{self.credentials["site"]}/wp-json/wp/v2/{path}/?per_page=100&&context=edit'
        s = requests.Session()
        s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
        response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))

        if response.status_code == 200:
            log(f'✅ AUTH Connection to new site {self.credentials["site"]}/{path} sucess', 'h1')
        else:
            log(f'⛔ AUTH Connection to new site {self.credentials["site"]}/{path} failed: {response.status_code}, {response.text}', 'h1')
            return

        return url, response.json()


    def apply_category(self, new_article, log):
        if new_article['categories']:
            category_id = ''
            fetch_url, fetched_categories = self.connect_to_wordpress('categories', log)
            
            #Check if category exists in the database
            for fetched_category in fetched_categories:
                log(f'🔍 Checking if category {fetched_category["name"]} exists in the database', 'h2')
                if fetched_category['name'] == new_article['categories']:
                    log(f'✅ Category {fetched_category["name"]} found in the database, returning category id', 'h3')
                    category_id = fetched_category['id']
                    return category_id
            #If category_id is empy it indicates that no categories was found in the db
            if category_id == '':
                category = ({
                        "name": new_article['categories'],
                        "slug": slugify(new_article['categories']),
                        "description": new_article['categories_desc'],
                        "parent": 0
                        })
                #Create category in the database
                log(f' 🟢 Creating new category {new_article["categories"]} in the database', 'h3')
                r = requests.post(
                    fetch_url,
                    json=category,
                    auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                    headers={"Content-Type": "application/json"}
                )
                if r.status_code == 201:
                    category_json = r.json()
                    log(f' ✅ Category {new_article["categories"]} created in the database, returning category id', 'h4')
                    category_id = category_json['id']
                    return category_id
                else:
                    log(f'❌ Category request post failed ❌', 'h1')
                    return None
            
            return None
            


    def apply_tags(self, new_article, log):
        log(f' 🟢 Applying tags to post {new_article["tags"]}', 'h2')
        if new_article['tags']:
            apply_tag_ids_arr = []
            fetched_fuzzy_tags_arr = []
            fetch_url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags/?per_page=100&&context=edit'
            tags = [t.strip() for t in new_article['tags']] if isinstance(new_article['tags'], list) else [t.strip() for t in new_article['tags'].split(',')]
            for tag in tags:
                log(f' 🔍 Checking if tag {tag} exists in the database', 'h3')
                #See if article tags exist in the database, if so apply tags to array.
                url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags?slug={slugify(tag)}'
                s = requests.Session()
                s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
                tag_response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))
                tag_response_json = tag_response.json()
                #If no tags are found, create them
                if tag_response_json == []:
                    log(f' 🔍 Tag {tag} not found in the database, creating new tag', 'h4')
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
                        log(f' ✅ Tag {tag} created in the database, returning tag id', 'h4')
                        tag_json = r.json()
                        apply_tag_ids_arr.append(tag_json['id'])
                    else:
                        log(f'❌ Tag {tag} data failed request ❌', 'h1')
                        return None
                else:
                    log(f' ✅ Tag {tag} found in the database, returning tag id', 'h4')
                    apply_tag_ids_arr.append(tag_response_json[0]['id'])

            return apply_tag_ids_arr

    def upload_and_convert_img(self, new_article, webp_bytes, caption, log):
        
        lib_url = f'https://{self.credentials["site"]}/wp-json/wp/v2/media'

        filename = f"{slugify(new_article['image_title'])}.webp"
        
        r = requests.post(
            lib_url,
            files={'file': (filename, webp_bytes, 'image/webp')},
            auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
        
        if r.status_code == 201:
            data = r.json()
            
            media_id = data["id"]
            log(f' ✅ Image id for post {new_article["title"]}: {media_id}', 'h4')
            
            # Update image metadata
            update_response = requests.post(
                f"{lib_url}/{media_id}",
                json={"alt_text": new_article['image_desc'], "caption": caption},
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )
            log(f' Image metadata update status: {update_response.status_code}', 'h4')
            
            return media_id
        else:
            log(f' ❌ Image upload failed: for post {new_article["title"]}: {r.status_code}, {r.text}', 'h1')
            return None


    def image_decision(self, open_ai, new_article, log):
        image_webp = ''
        image_library_id = ''
        log(f' 🟢🟢 Image decision for post {new_article["title"]}', 'h2')

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

        whitelist_response = open_ai.send_prompt(prompt, log, instructions, version='gpt-5-nano')
        ai_whitelist_response = json.loads(whitelist_response)
        log(f' 🔍 Image decision for post {new_article["title"]} response: {ai_whitelist_response}', 'h3')
        #Convert the none licensed image to webp and return it
        if ai_whitelist_response['License']:
            img = Image.open(BytesIO(requests.get(new_article['media']).content))
            output = BytesIO()
            img.convert("RGB").save(output, format="WEBP", quality=80)
            image_webp_bytes = output.getvalue()
            img_id = self.upload_and_convert_img(new_article, image_webp_bytes, new_article['image_caption'], log)
            return img_id
        else:
            #If no licensed image is found, search the database for a matching image
            url = f"https://{self.credentials['site']}/wp-json/wp/v2/media?search={slugify(ai_whitelist_response['Searchword'])}"
            log(f' 🔍 Searching for images with searchword: {slugify(ai_whitelist_response["Searchword"])}', 'h3')    
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
                log(f' 🔍 Fetched images for post {new_article["title"]}: {fetched_imgs}', 'h3')
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
                database_img_response = open_ai.send_prompt(prompt, log, instructions, version='gpt-5-nano')
                database_img_response_json = json.loads(database_img_response)
                log(f' 🔍 Database image response for post {new_article["title"]}: {database_img_response_json}', 'h3')
                #If an image is found, return it
                if database_img_response_json and database_img_response_json['image_id']:
                    img_id = database_img_response_json['image_id']
                    return img_id
                else:
                    log(f' ❌ No images found in database for post {new_article["title"]}', 'h1')
                    return None

        #Generate an image with AI and return it as webp
        log(f' 🟢 AI generating new image for post {new_article["title"]}', 'h2')
        image_webp_bytes = open_ai.generate_img(
            new_article['title'], new_article['media'], log
        )
        ##Upload the image to the database and return the id
        img_id = self.upload_and_convert_img(new_article, image_webp_bytes, 'AI Genereret', log)
        return img_id
                

    def publish_post(self, articles, img_id, log):
        if articles == []:
            log('❌ No new articles to publish to WordPress ❌', 'h1')
            return

        for new_article in articles:
            log(f' Preparing metadata for post {new_article["title"]}', 'h1')


            category_id = self.apply_category(new_article, log)
            tag_ids = self.apply_tags(new_article, log)
            
            # Skip posting if image upload failed
            if img_id is None:
                log('❌ Skipping post due to failed image upload ❌', 'h2')
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

            log(f' Ready article metadata for post {new_article["title"]}', 'h1')

            if r.status_code == 201:
                log(f'✅ Post {new_article["title"]} published to WordPress sucessfully', 'h1')
            else:
                log(f'⛔ Post {new_article["title"]} failed to publish to WordPress: {r.status_code}, {r.text}', 'h1')
            return