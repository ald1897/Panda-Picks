# from logging import Logger
# import requests
# import json
# from panda_picks import config
#
# logger = Logger(__name__)
#
# # panda_picks/data/get_pff_grades.py
#
# # API endpoint
# url = "https://premium.pff.com/api/v1/teams/overview?league=nfl&season=2024&week=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18"
#
# # Full raw cookie string from your browser
# cookie_string = """_sharedID=d746d55c-5ace-438b-8c48-f17e7f2acb37; _sharedID_cst=zix7LPQsHA%3D%3D; _scid=ZmLgrHw1ShV7elAeyGzZyXJ3rCySKD7G; _ga=GA1.1.1922296995.1752777991; _tt_enable_cookie=1; _ttp=01K0CVB8DD0AFJ9A64NCZ4JESH_.tt.1; _cc_id=76b7450d12b79cd52ddb450740ad9d3; panoramaId_expiry=1753382791240; panoramaId=e1a96061bbb888e4a6cc2f01abc716d539386eff4f901d011721eb990fd6962e; panoramaIdType=panoIndiv; _ScCbts=%5B%22340%3Bchrome.2%3A2%3A5%22%2C%22414%3Bchrome.2%3A2%3A5%22%5D; FPID=FPID2.2.sBmQAzg2G4hU0GIhi%2FFF37ZOKQDRbZVeOcc9zD9l2oo%3D.1752777991; FPAU=1.2.1328572672.1752777991; _gtmeec=e30%3D; _fbp=fb.1.1752777991242.1438270638; _sharedid=27e5d58c-138e-4f0e-9ea2-4f1ceafef7be; _sharedid_cst=zix7LPQsHA%3D%3D; cto_bundle=NGQRHl9SNUtNdHpKNnhtRlpteDRhV0xrNWt2MVNWekRGMzJ1TEZ2a1FVUmVPdyUyRjR3UFpzQ0pJMkJVUkQ2Y2Z1R1NnU0ZLanklMkZXMHdUeGVtaVJrdXBKSjNjOW9IbUkyaDRUOWlrdjF0cDFLNWZCcTglM0Q; cto_bidid=MLLCtl9QbldZSHpVc2syb1dneDRzM3NHWFF5RlBTOWk1aDB6b1RCMGdDVVBNU0h3VUdaeEwlMkZYRWMzRFhScEo4ZzAlMkJEcEJ3QjdZVVRpTHZQaWNrSTZYalZJbkElM0QlM0Q; _sctr=1%7C1752724800000; external_id=08ba12a8-5a4d-4d2d-9196-f8506bed90e1; _ga_470ETDQ3X2=GS2.1.s1753127429$o1$g1$t1753127565$j60$l0$h0; _premium_key=SFMyNTY.g3QAAAABbQAAABZndWFyZGlhbl9kZWZhdWx0X3Rva2VubQAAAmNleUpoYkdjaU9pSklVelV4TWlJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpRY21WdGFYVnRJaXdpWlhod0lqb3hOelV6TVRNeE1qQTRMQ0pwWVhRaU9qRTNOVE14TWpjMk1EZ3NJbWx6Y3lJNklsQnlaVzFwZFcwaUxDSnFkR2tpT2lKbU56RXlNR1ptWWkweE5EZGpMVFJoWVdFdE9HUm1ZUzFsWVRNNU5EazNNamxsWXpFaUxDSnVZbVlpT2pFM05UTXhNamMyTURjc0luQmxiU0k2ZXlKaFlXWWlPakVzSW01allXRWlPakVzSW01bWJDSTZNU3dpZFdac0lqb3hmU3dpYzNWaUlqb2llMXdpWlcxaGFXeGNJanBjSW1Gc1pYaGthV05yYVc1emIyNHdORUJuYldGcGJDNWpiMjFjSWl4Y0ltWmxZWFIxY21WelhDSTZXMTBzWENKbWFYSnpkRjl1WVcxbFhDSTZiblZzYkN4Y0lteGhjM1JmYm1GdFpWd2lPbTUxYkd3c1hDSjFhV1JjSWpwY0lqVTFNVGt4TXpBMUxXWmlZVEV0TkdVeU15MWhaR1ppTFRnNFlqQTVOREE1WVdVNE0xd2lMRndpZG1WeWRHbGpZV3hjSWpwY0lrTnZibk4xYldWeVhDSjlJaXdpZEhsd0lqb2lZV05qWlhOekluMC51R3k0cDZDUmlZMWcyaVRrRHpmYnJ1WGNpRVVfU0RMMFVOVWdhbHpqOXdROGN5dzkzaGpHNzJLd2RCVnQxYmtWcDAyWlQ4QTJQbEpIRHVsMkNhMnhWdw.MlCFU-AwOvkzVuRmL5vSSWYIwTZXYsq195U_ncrSvHg; c_groot_access_token=OWswAqg-EE3YmZR5xLYCZ6vdlQZH9Ts7i9mvj00N_bMSuqOuKbr2DtI_z_2oEUb6; c_groot_access_ts=2025-07-21T19:53:28Z; c_groot_refresh_token=nMCo-uQg_9Fiz5v6nLyNqN_Uqn6NxT1UGOwYRG0uprRKL_0EGGccubB8GBWC9_Lc; _hp2_ses_props.2100373990=%7B%22r%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%2C%22ts%22%3A1753127608585%2C%22d%22%3A%22premium.pff.com%22%2C%22h%22%3A%22%2Fnfl%2Fpositions%2F2021%2FREGPO%22%7D; FPLC=1VOaCa4drN3j78GC4Mdd1xSAkQwpJi3Rd09%2FrC8uZO9a8HS5EgIuamP7kFAnvv2dwq1Lk7Oa6GbPZVb%2FJidnPcOLZELByQ6ZSFAP4ix9cWpYLUL8tDPNE1rkp%2BkinA%3D%3D; _ga_123456789=GS2.1.s1753127608$o3$g1$t1753127663$j5$l0$h73379027; _scid_r=dOLgrHw1ShV7elAeyGzZyXJ3rCySKD7Gg1TmDQ; _hp2_id.2100373990=%7B%22userId%22%3A%224254177650532308%22%2C%22pageviewId%22%3A%223221113891007720%22%2C%22sessionId%22%3A%223525065286420373%22%2C%22identity%22%3A%2255191305-fba1-4e23-adfb-88b09409ae83%22%2C%22trackerVersion%22%3A%224.0%22%2C%22identityField%22%3Anull%2C%22isIdentified%22%3A1%7D; ttcsid_CJ607MBC77U3K5NQN0BG=1753127608731::wOtZgN8pzF7xPXmj14XR.2.1753127772705; ttcsid=1753127608731::1si_cLOWCWqQmJtr5Dm7.2.1753127772705"""
#
# # Convert cookie string into dictionary
# cookies = dict(item.split("=", 1) for item in cookie_string.split("; "))
#
# # Optional: Realistic headers to mimic browser request
# headers = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
#     "Accept": "application/json",
#     "Accept-Encoding": "gzip, deflate, br",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Referer": "https://premium.pff.com/",
# }
#
# # Make the API request
# response = requests.get(url, headers=headers, cookies=cookies)
# # print(response.json())
# print(f"Request URL: {url}")
# print(f"Request Headers: {headers}")
# print(f"Request Cookies: {cookies}")
# print(f"Response Status Code: {response.status_code}")
# print(f"Response Headers: {response.headers}")
# print(f"Response Content: {response.text[:500]}")  # Log first 500 characters of response content
# # logger.debug("Fetching PFF Grades...")
#
# # Check and print result
# if response.status_code == 200:
#     print("✅ Success:")
#     # logger.info("PFF Grades fetched successfully.")
#     # data = response.json()
#     # logger.info(f"Data: {json.dumps(data, indent=2)}")
# else:
#     print(f"❌ Error: {response.status_code}")
#     print(response.text)
import requests
import pandas as pd
from panda_picks import config

# API endpoint
url = "https://premium.pff.com/api/v1/teams/overview?league=nfl&season=2024&week=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18"

# Headers and cookies for the API request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://premium.pff.com/",
}

cookie_string = """_sharedID=d746d55c-5ace-438b-8c48-f17e7f2acb37; _sharedID_cst=zix7LPQsHA%3D%3D; _scid=ZmLgrHw1ShV7elAeyGzZyXJ3rCySKD7G; _ga=GA1.1.1922296995.1752777991; _tt_enable_cookie=1; _ttp=01K0CVB8DD0AFJ9A64NCZ4JESH_.tt.1; _cc_id=76b7450d12b79cd52ddb450740ad9d3; panoramaId_expiry=1753382791240; panoramaId=e1a96061bbb888e4a6cc2f01abc716d539386eff4f901d011721eb990fd6962e; panoramaIdType=panoIndiv; _ScCbts=%5B%22340%3Bchrome.2%3A2%3A5%22%2C%22414%3Bchrome.2%3A2%3A5%22%5D; FPID=FPID2.2.sBmQAzg2G4hU0GIhi%2FFF37ZOKQDRbZVeOcc9zD9l2oo%3D.1752777991; FPAU=1.2.1328572672.1752777991; _gtmeec=e30%3D; _fbp=fb.1.1752777991242.1438270638; _sharedid=27e5d58c-138e-4f0e-9ea2-4f1ceafef7be; _sharedid_cst=zix7LPQsHA%3D%3D; cto_bundle=NGQRHl9SNUtNdHpKNnhtRlpteDRhV0xrNWt2MVNWekRGMzJ1TEZ2a1FVUmVPdyUyRjR3UFpzQ0pJMkJVUkQ2Y2Z1R1NnU0ZLanklMkZXMHdUeGVtaVJrdXBKSjNjOW9IbUkyaDRUOWlrdjF0cDFLNWZCcTglM0Q; cto_bidid=MLLCtl9QbldZSHpVc2syb1dneDRzM3NHWFF5RlBTOWk1aDB6b1RCMGdDVVBNU0h3VUdaeEwlMkZYRWMzRFhScEo4ZzAlMkJEcEJ3QjdZVVRpTHZQaWNrSTZYalZJbkElM0QlM0Q; _sctr=1%7C1752724800000; external_id=08ba12a8-5a4d-4d2d-9196-f8506bed90e1; _ga_470ETDQ3X2=GS2.1.s1753127429$o1$g1$t1753127565$j60$l0$h0; _premium_key=SFMyNTY.g3QAAAABbQAAABZndWFyZGlhbl9kZWZhdWx0X3Rva2VubQAAAmNleUpoYkdjaU9pSklVelV4TWlJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpRY21WdGFYVnRJaXdpWlhod0lqb3hOelV6TVRNeE1qQTRMQ0pwWVhRaU9qRTNOVE14TWpjMk1EZ3NJbWx6Y3lJNklsQnlaVzFwZFcwaUxDSnFkR2tpT2lKbU56RXlNR1ptWWkweE5EZGpMVFJoWVdFdE9HUm1ZUzFsWVRNNU5EazNNamxsWXpFaUxDSnVZbVlpT2pFM05UTXhNamMyTURjc0luQmxiU0k2ZXlKaFlXWWlPakVzSW01allXRWlPakVzSW01bWJDSTZNU3dpZFdac0lqb3hmU3dpYzNWaUlqb2llMXdpWlcxaGFXeGNJanBjSW1Gc1pYaGthV05yYVc1emIyNHdORUJuYldGcGJDNWpiMjFjSWl4Y0ltWmxZWFIxY21WelhDSTZXMTBzWENKbWFYSnpkRjl1WVcxbFhDSTZiblZzYkN4Y0lteGhjM1JmYm1GdFpWd2lPbTUxYkd3c1hDSjFhV1JjSWpwY0lqVTFNVGt4TXpBMUxXWmlZVEV0TkdVeU15MWhaR1ppTFRnNFlqQTVOREE1WVdVNE0xd2lMRndpZG1WeWRHbGpZV3hjSWpwY0lrTnZibk4xYldWeVhDSjlJaXdpZEhsd0lqb2lZV05qWlhOekluMC51R3k0cDZDUmlZMWcyaVRrRHpmYnJ1WGNpRVVfU0RMMFVOVWdhbHpqOXdROGN5dzkzaGpHNzJLd2RCVnQxYmtWcDAyWlQ4QTJQbEpIRHVsMkNhMnhWdw.MlCFU-AwOvkzVuRmL5vSSWYIwTZXYsq195U_ncrSvHg; c_groot_access_token=OWswAqg-EE3YmZR5xLYCZ6vdlQZH9Ts7i9mvj00N_bMSuqOuKbr2DtI_z_2oEUb6; c_groot_access_ts=2025-07-21T19:53:28Z; c_groot_refresh_token=nMCo-uQg_9Fiz5v6nLyNqN_Uqn6NxT1UGOwYRG0uprRKL_0EGGccubB8GBWC9_Lc; _hp2_ses_props.2100373990=%7B%22r%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%2C%22ts%22%3A1753127608585%2C%22d%22%3A%22premium.pff.com%22%2C%22h%22%3A%22%2Fnfl%2Fpositions%2F2021%2FREGPO%22%7D; FPLC=1VOaCa4drN3j78GC4Mdd1xSAkQwpJi3Rd09%2FrC8uZO9a8HS5EgIuamP7kFAnvv2dwq1Lk7Oa6GbPZVb%2FJidnPcOLZELByQ6ZSFAP4ix9cWpYLUL8tDPNE1rkp%2BkinA%3D%3D; _ga_123456789=GS2.1.s1753127608$o3$g1$t1753127663$j5$l0$h73379027; _scid_r=dOLgrHw1ShV7elAeyGzZyXJ3rCySKD7Gg1TmDQ; _hp2_id.2100373990=%7B%22userId%22%3A%224254177650532308%22%2C%22pageviewId%22%3A%223221113891007720%22%2C%22sessionId%22%3A%223525065286420373%22%2C%22identity%22%3A%2255191305-fba1-4e23-adfb-88b09409ae83%22%2C%22trackerVersion%22%3A%224.0%22%2C%22identityField%22%3Anull%2C%22isIdentified%22%3A1%7D; ttcsid_CJ607MBC77U3K5NQN0BG=1753127608731::wOtZgN8pzF7xPXmj14XR.2.1753127772705; ttcsid=1753127608731::1si_cLOWCWqQmJtr5Dm7.2.1753127772705"""
cookies = dict(item.split("=", 1) for item in cookie_string.split("; "))

def fetch_pff_grades():
    """Fetch team grades from the PFF API."""
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Error fetching data from PFF API: {e}")

def process_grades(data):
    """Process the API response into a structured DataFrame."""
    try:
        # Extract the team_overview list
        teams_data = data.get("team_overview", [])
        if not teams_data:
            raise ValueError("No team data found in API response.")

        # Convert to DataFrame
        df = pd.DataFrame(teams_data)

        # Select and rename columns to match the desired format
        column_mapping = {
            "abbreviation": "TEAM",
            "grades_overall": "OVR",
            "grades_offense": "OFF",
            "grades_pass": "PASS",
            "grades_run": "RUN",
            "grades_defense": "DEF",
            "grades_run_defense": "RDEF",
            "grades_pass_rush_defense": "PRSH",
            "grades_coverage_defense": "COV",
            "grades_tackle": "TACK",
            "grades_pass_block": "PBLK",
            "grades_run_block": "RBLK",
            "grades_pass_route": "RECV",
            "wins": "WINS",
            "losses": "LOSSES",
            "ties": "TIES",
            "points_scored": "PTS_SCORED",
            "points_allowed": "PTS_ALLOWED",
        }
        df = df.rename(columns=column_mapping)

        # Keep only the required columns
        required_columns = list(column_mapping.values())
        df = df[required_columns]

        return df
    except Exception as e:
        raise Exception(f"Error processing grades data: {e}")

def save_grades_to_csv(df, output_path):
    """Save the processed grades DataFrame to a CSV file."""
    try:
        df.to_csv(output_path, index=False)
        print(f"Team grades saved to {output_path}")
    except Exception as e:
        raise Exception(f"Error saving grades to CSV: {e}")

def getGrades():
    """Fetch, process, and save team grades."""
    try:
        # Fetch data from the API
        raw_data = fetch_pff_grades()

        # Process the data into a structured format
        grades_df = process_grades(raw_data)

        # Save the processed data to a CSV file
        output_file = config.TEAM_GRADES_CSV
        save_grades_to_csv(grades_df, output_file)

        return True
    except Exception as e:
        print(f"Error in getGrades: {e}")
        return False

if __name__ == "__main__":
    getGrades()