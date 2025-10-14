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
            log(f'✅ AUTH Connection to new site {self.credentials["site"]}/{path} sucess', 'list')
        else:
            log(f'⛔ AUTH Connection to new site {self.credentials["site"]}/{path} failed: {response.status_code}, {response.text}', 'list')
            return

        return url, response.json()


    def apply_category(self, new_article, log):
        log(f'🔍 Applying category to post {new_article["id"]}', 'h3')
        if new_article['categories']:
            category_id = ''
            fetch_url, fetched_categories = self.connect_to_wordpress('categories', log)
            
            #Check if category exists in the database
            for fetched_category in fetched_categories:
                if fetched_category['name'] == new_article['categories']:
                    log(f'✅ Category {fetched_category["name"]} found in the database, returning category id', 'list')
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
                log(f'🟢 Creating new category {new_article["categories"]} in the database', 'list')
                r = requests.post(
                    fetch_url,
                    json=category,
                    auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                    headers={"Content-Type": "application/json"}
                )
                if r.status_code == 201:
                    category_json = r.json()
                    log(f'✅ Category {new_article["categories"]} created in the database, returning category id', 'list')
                    category_id = category_json['id']
                    return category_id
                else:
                    log(f'❌ Category request post failed ❌', 'list')
                    return None
            
            return None
            


    def apply_tags(self, new_article, log):
        log(f' 🟢 Applying tags to post {new_article["tags"]}', 'h3')
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
                    log(f'🔍 Tag {tag} not found in the database, creating new tag', 'list')
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
                        log(f'✅ Tag {tag} created in the database, returning tag id', 'list')
                        tag_json = r.json()
                        apply_tag_ids_arr.append(tag_json['id'])
                    else:
                        log(f'❌ Tag {tag} data failed request ❌', 'list')
                        return None
                else:
                    log(f'✅ Tag {tag} found in the database, returning tag id', 'list')
                    apply_tag_ids_arr.append(tag_response_json[0]['id'])

            return apply_tag_ids_arr

    def upload_and_convert_img(self, new_article, webp_bytes, caption, image_description, log):
        log(f'🔍 Uploading image for post {new_article["id"]}', 'h2')
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
            
            # Update image metadata
            update_response = requests.post(
                f"{lib_url}/{media_id}",
                json={"alt_text": image_description, "caption": caption},
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )
            log(f'✅ Image upload and metadata update successful for post {new_article["id"]}: {update_response.status_code}', 'list')
            
            return media_id
        else:
            log(f'❌ Image upload failed for post {new_article["id"]}: {r.status_code}, {r.text}', 'list')
            return None


    def image_decision(self, open_ai, new_article, log):
        log(f'🔍 Image decision for post {new_article["id"]}', 'h2')
        image_webp = ''
        image_library_id = ''

        #Investigate if the image has no License and therefore can be used.
        prompt=f"Billedets caption = {new_article['image_caption']}"
        instructions=f"""
        Ud fra denne caption skal du vurdere om billedet er licensfrit.
        Alle billeder fra TikTok, Facebook, Instagram, youtube, Google Maps osv er skærmbilleder, derfor er de godkendte og licensfrie.
        Såvel som billeder fra gratis sites som Pexels, Pixabay, Unsplash og andre du kender.

        Alt i alt, skal du vurdere om dette billede er licensfrit og om vi kan benytte det til vores artikel.

        Vi skal bruge et dansk søgeord ud fra titlen {new_article['image_title']}.
        F.eks hvis titlen er 'Edderkop kravler hen af gulvet' skal søgeordet bare være Edderkop.
        Hvis artiklen omhandler en privatperson hvor billedegenerering ikke er tilladt, som fx 'Jonas Vingegaard',
        skal søgeordet være noget som fx 'Cykelrytter', 'Tour de France'.

        Oversæt til dansk og skriv en billedebeskrivelse ud fra denne beskrivelse: {new_article['image_desc']}.
        Den skal indeholde søgeord som er relevante for artiklen og billedet.

        Hvis ingen caption, er License automatisk False

        Du skal returnere i dette JSON format ud fra om det er licensfrit eller ikke.
        False = Ikke Licensfrit
        True = Licensfrit

        {{
            "License": bool,
            "Reason": string,
            "Searchword": string,
            "image_description": string
        }}
        """

        whitelist_response = open_ai.send_prompt(prompt, log, instructions, version='gpt-5-nano')
        ai_whitelist_response = json.loads(whitelist_response)
        log(f'🔍 Image decision for post {new_article["id"]} response: `{ai_whitelist_response}`', 'list')
        #Convert the none licensed image to webp and return it
        if ai_whitelist_response['License']:
            img = Image.open(BytesIO(requests.get(new_article['media']).content))
            output = BytesIO()
            img.convert("RGB").save(output, format="WEBP", quality=80)
            image_webp_bytes = output.getvalue()
            img_id = self.upload_and_convert_img(new_article, image_webp_bytes, new_article['image_caption'], ai_whitelist_response['image_description'], log)
            return img_id
        else:
            #If no licensed image is found, search the database for a matching image
            url = f"https://{self.credentials['site']}/wp-json/wp/v2/media?search={slugify(ai_whitelist_response['Searchword'])}"
            log(f'🔍 Searching for images with searchword: {slugify(ai_whitelist_response["Searchword"])}', 'list')    
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
                log(f'🔍 Fetched images for post {new_article["id"]}: {fetched_imgs}', 'list')
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
                #If an image is found, return it
                if database_img_response_json and database_img_response_json['image_id']:
                    log(f'🔍 Database image response for post {new_article["id"]}: `{database_img_response_json}`', 'list')
                    img_id = database_img_response_json['image_id']
                    return img_id
                else:
                    log(f'❌ No images found in database for post {new_article["id"]}', 'list')
                    return None

        #Generate an image with AI and return it as webp
        image_webp_bytes = open_ai.generate_img(
            new_article['title'], new_article['media'], log
        )
        ##Upload the image to the database and return the id
        img_id = self.upload_and_convert_img(new_article, image_webp_bytes, 'AI Genereret', ai_whitelist_response['image_description'], log)
        return img_id
                

    def publish_post(self, articles, img_id, log):
        if articles == []:
            log('❌ No new articles to publish to WordPress ❌', 'h2')
            return
        else:
            log(f'🔍 Preparing metadata for post {articles[0]["title"]}', 'h2')

        for new_article in articles:
            if new_article['categories']:
                category_id = self.apply_category(new_article, log)
            else:
                category_id = ''

            if new_article['tags']:
                tag_ids = self.apply_tags(new_article, log)
            else:
                tag_ids = ''
            
            # Skip posting if image upload failed
            if img_id is None:
                log('❌ Skipping post due to failed image upload ❌', 'list')
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

            if r.status_code == 201:
                log(f'✅ Post {new_article["id"]} published to WordPress sucessfully', 'h2')
            else:
                log(f'⛔ Post {new_article["id"]} failed to publish to WordPress: {r.status_code}, {r.text}', 'h2')
            log(f'🌐 Link to post: https://{self.credentials["site"]}/wp-json/wp/v2/posts/{new_article["id"]}', 'list')
            return