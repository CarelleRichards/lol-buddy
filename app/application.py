from datetime import datetime
import time
import re
import boto3
from flask import Flask, render_template, request, redirect, url_for, session
import requests
import aiohttp
import asyncio
import certifi
import ssl
from urllib.parse import quote, unquote
from io import StringIO
from html.parser import HTMLParser

application = Flask(__name__)
application.secret_key = "" # Session key
api_key = ""  # Riot API key
registration_error = None
login_error = None
search_error = None
users_key = ""  # AWS API Gateway key
cloud_search_url = "http://search-champions-ieqqmszs35bwkvlrsfn5466j34.us-east-1.cloudsearch.amazonaws.com/2013-01-01/search"

# Configure for Riot API because aiohttp doesn't recognise ssl cert.
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(certifi.where())


# ----------------------
# ROUTING
# ----------------------

@application.route("/", methods=["POST", "GET"])
def index():
    if check_session():
        if request.method == "POST":
            search_region = request.form.get("region")
            search_player_name = request.form["player-name"]
            return redirect(url_for("player_profile", search_region=search_region, search_player_name=search_player_name))
        oce_leaderboard = get_leaderboard("oc1")
        na_leaderboard = get_leaderboard("na1")
        return render_template("index.html", username=session["username"], oce_leaderboard=oce_leaderboard, na_leaderboard=na_leaderboard)
    else:
        return render_template("login.html")


@application.route("/favourites")
def favourites():
    if check_session():
        favourites_list = get_favourites_list()
        oce_leaderboard = get_leaderboard("oc1")
        na_leaderboard = get_leaderboard("na1")
        return render_template("favourites.html", username=session["username"], favourites=favourites_list,
                               oce_leaderboard=oce_leaderboard, na_leaderboard=na_leaderboard)
    else:
        return render_template("login.html")


@application.route("/champions/search-<term>/class-<champion_class>/difficulty-<difficulty>/sort-<sort>", methods=["POST", "GET"])
def search_champions(term, champion_class, difficulty, sort):
    if check_session():
        champion_results = get_champions(term, champion_class, difficulty, sort)
        if request.method == "POST":
            search_input = encode_url(request.form["champion-name"])
            if not search_input:
                search_input = "all"
            champion_class_input = request.form.get("champion-class")
            champion_difficulty_input = request.form.get("champion-difficulty")
            sort_input = request.form.get("sort")
            return redirect(url_for("search_champions", term=search_input, champion_class=champion_class_input,
                                    difficulty=champion_difficulty_input, sort=sort_input))
        else:
            return render_template("champions.html", username=session["username"], champion_results=champion_results,
                                   term=term, champion_class=champion_class, difficulty=difficulty, sort=sort)
    else:
        return render_template("login.html")


@application.route("/player-profile/<search_region>/<search_player_name>")
def player_profile(search_region, search_player_name):
    if check_session():
        player_info = get_player_info(search_region, search_player_name)
        if player_info:
            match_history = asyncio.run(get_match_history(search_region, player_info["puuid"]))
            role_stats = get_role_stats(match_history, player_info)
            win_rate = get_win_rate(match_history, player_info)
            queue_types = get_queue_types()
            player_rank_info = get_player_rank_info(search_region, player_info["id"])
            is_favourite = check_favourite(search_region, search_player_name)
            return render_template("player-profile.html", username=session["username"], player_info=player_info,
                                   match_history=match_history, queue_types=queue_types, player_rank_info=player_rank_info,
                                   search_region=search_region, role_stats=role_stats, win_rate=win_rate, is_favourite=is_favourite)
        else:
            return render_template("player-profile.html", username=session["username"], player_info=player_info, search_region=search_region,
                                   search_error=search_error)
    else:
        return render_template("login.html")


@application.route("/champion-profile/<champion_name>")
def champion_profile(champion_name):
    if check_session():
        champion_data = get_champion_data(champion_name)
        return render_template("champion-profile.html", username=session["username"], champion_data=champion_data)
    else:
        return render_template("login.html")


@application.route("/favourite-player/<region>/<player_name>")
def favourite_player(region, player_name):
    if check_session():
        put_favourite(region, player_name)
        return redirect(url_for("favourites"))


@application.route("/unfavourite-player/<region>/<player_name>")
def unfavourite_player(region, player_name):
    if check_session():
        remove_favourite(region, player_name)
        return redirect(url_for("favourites"))


@application.route("/login", methods=["POST", "GET"])
def login():
    global login_error
    login_error = None
    if check_session():
        return redirect(url_for("index"))
    else:
        if request.method == "POST":
            email_input = request.form["email"]
            password_input = request.form["password"]
            existing_user = login_user(email_input, password_input)
            if existing_user:
                make_session(existing_user[0]["email"], existing_user[0]["username"])
                return redirect(url_for("index"))
    return render_template("login.html", login_error=login_error)


@application.route("/logout")
def logout():
    remove_session()
    return redirect(url_for("login"))


@application.route("/register", methods=["POST", "GET"])
def register():
    global registration_error
    registration_error = None
    if request.method == "POST":
        email_input = request.form["email"]
        username_input = request.form["username"]
        password_input = request.form["password"]
        new_user = register_user(email_input, username_input, password_input)
        if new_user:
            return redirect(url_for("login"))
    return render_template("register.html", registration_error=registration_error)


# ----------------------
# CUSTOM FILTERS
# ----------------------

# For strip_tags() function to remove any HTML from text
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


# Remove any HTML from text
@application.template_filter("strip_tags")
def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


# Return champion difficulty
@application.template_filter("difficulty")
def difficulty(num):
    full_star = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="56" fill="currentColor" class="bi bi-star-fill" viewBox="0 0 16 21"><path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z"/></svg> '
    outline_star = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="56" fill="currentColor" class="bi bi-star" viewBox="0 0 16 21"><path d="M2.866 14.85c-.078.444.36.791.746.593l4.39-2.256 4.389 2.256c.386.198.824-.149.746-.592l-.83-4.73 3.522-3.356c.33-.314.16-.888-.282-.95l-4.898-.696L8.465.792a.513.513 0 0 0-.927 0L5.354 5.12l-4.898.696c-.441.062-.612.636-.283.95l3.523 3.356-.83 4.73zm4.905-2.767-3.686 1.894.694-3.957a.565.565 0 0 0-.163-.505L1.71 6.745l4.052-.576a.525.525 0 0 0 .393-.288L8 2.223l1.847 3.658a.525.525 0 0 0 .393.288l4.052.575-2.906 2.77a.565.565 0 0 0-.163.506l.694 3.957-3.686-1.894a.503.503 0 0 0-.461 0z"/></svg> '
    if num == 0 or num == 1 or num == 2 or num == 3:
        difficulty_string = full_star + outline_star + outline_star + "<span class='ml-1'>Easy</span>"
    elif num == 4 or num == 5 or num == 6 or num == 7:
        difficulty_string = full_star + full_star + outline_star + "<span class='ml-1'>Medium</span>"
    elif num == 8 or num == 9 or num == 10:
        difficulty_string = full_star + full_star + outline_star + "<span class='ml-1'>Hard</span>"
    return difficulty_string


# Return champion id
@application.template_filter("get_champion_id")
def get_champion_id(champion_name):
    champion_data = get_champion_data(champion_name)
    return champion_data["id"]


# Return champion nickname for champions with long names
@application.template_filter("nickname")
def nickname(champion):
    name = None
    if champion == "Nunu & Willump":
        name = "Nunu"
    elif champion == "Renata Glasc":
        name = "Renata"
    elif champion == "Twisted Fate":
        name = "Twisted"
    elif champion == "Aurelion Sol":
        name = "Aurelion"
    else:
        name = champion
    return name


# Convert unix dates
@application.template_filter("ctime")
def convert_time(t):
    unix = int(str(t)[:10])
    date = datetime.fromtimestamp(unix)
    date_format = date.strftime("%d %b")
    return date_format


# Convert region
@application.template_filter("format_region")
def format_region(region):
    region_formatted = None
    if region == "OC1":
        region_formatted = "Oceania"
    if region == "NA1":
        region_formatted = "North America"
    return region_formatted


# Get image from S3
@application.template_filter("get_image")
def get_image(image):
    s3_client = boto3.client("s3")
    response = s3_client.generate_presigned_url("get_object", ExpiresIn=43200, Params={"Bucket": "assessment3-s3749114", "Key": image})
    return response


# Get rank emblem images from S3
@application.template_filter("get_ranked_emblem")
def get_ranked_emblem(rank):
    file_name = None
    if rank == "IRON":
        file_name = "Emblem_Iron.png"
    if rank == "BRONZE":
        file_name = "Emblem_Bronze.png"
    elif rank == "SILVER":
        file_name = "Emblem_Silver.png"
    elif rank == "GOLD":
        file_name = "Emblem_Gold.png"
    elif rank == "PLATINUM":
        file_name = "Emblem_Platinum.png"
    elif rank == "DIAMOND":
        file_name = "Emblem_Diamond.png"
    elif rank == "MASTER":
        file_name = "Emblem_Master.png"
    elif rank == "GRANDMASTER":
        file_name = "Emblem_Grandmaster.png"
    elif rank == "CHALLENGER":
        file_name = "Emblem_Challenger.png"
    s3_client = boto3.client("s3")
    response = s3_client.generate_presigned_url("get_object", ExpiresIn=43200, Params={"Bucket": "assessment3-s3749114", "Key": file_name})
    return response


# Escapes any special chars for url
@application.template_filter("encode_url")
def encode_url(url):
    return quote(url)


# Escapes any special chars for url
@application.template_filter("unencode_url")
def unencode_url(url):
    return unquote(url)


# Adds space before capital letter
@application.template_filter("add_space")
def add_space(string):
    new_string = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", string)
    return quote(new_string)


# Formats rank to right format
@application.template_filter("format_rank")
def add_space(format_rank):
    formatted = None
    if format_rank == "RANKED_SOLO_5x5":
        formatted = "5x5 Ranked Solo"
    if format_rank == "RANKED_TEAM_5x5":
        formatted = "5x5 Ranked Team"
    return quote(formatted)


# ----------------------
# USERS
# ----------------------

# Calls user API (created with API Gateway) that triggers login_user Lambda function
def login_user(email_input, password_input):
    global login_error
    login_error = None
    if email_input != "" and password_input != "":
        api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/login?email=" + email_input + "&password=" + password_input
        headers = {"x-api-key": users_key}
        get_response = requests.get(api_url, headers=headers)
        if get_response.status_code == 200:
            return get_response.json()
        elif get_response.status_code == 404:
            login_error = get_response.json()["message"]
        else:
            login_error = "An error occurred"


# Calls user API (created with API Gateway) that triggers register_user Lambda function
def register_user(email_input, username_input, password_input):
    global registration_error
    registration_error = None
    if email_input != "" and password_input != "" and username_input != "":
        api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/register?email=" + email_input
        headers = {"x-api-key": users_key}
        get_response = requests.get(api_url, headers=headers)
        if get_response.status_code == 200:
            registration_error = get_response.json()["message"]
        elif get_response.status_code == 404:
            api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/register"
            myobj = {"email": email_input, "password": password_input, "username": username_input}
            headers = {"x-api-key": users_key}
            post_response = requests.post(api_url, json=myobj, headers=headers)
            if post_response.status_code == 200:
                return post_response.json()


# ----------------------
# USER FAVOURITES
# ----------------------

# Calls user API (created with API Gateway) that triggers favourite_player Lambda function
def put_favourite(region, player_name):
    api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/favourite?region=" + region
    myobj = {"email": session["email"], "player_name": player_name, "time_added": int(time.time())}
    headers = {"x-api-key": users_key}
    post_response = requests.post(api_url, json=myobj, headers=headers)
    if post_response.status_code == 200:
        return post_response.json()


# Calls user API (created with API Gateway) that triggers favourites_list Lambda function
def remove_favourite(region, player_name):
    api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/favourite?region=" + region
    myobj = {"email": session["email"], "player_name": player_name}
    headers = {"x-api-key": users_key}
    delete_response = requests.delete(api_url, json=myobj, headers=headers)
    if delete_response.status_code == 200:
        return delete_response.json()


# Calls user API (created with API Gateway) that triggers favourites_list Lambda function
def query_favourites(region):
    api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/favourites?email=" + session["email"] + "&region=" + region
    headers = {"x-api-key": users_key}
    get_response = requests.get(api_url, headers=headers)
    if get_response.status_code == 200:
        return get_response.json()


# Make favourites object, so we can add oc1 and na favourites together in a list
class Favourite:
    def __init__(self, player_name, region, image, time_added):
        self.player_name = player_name
        self.region = region
        self.image = image
        self.time_added = time_added


# Reurn true if player exists in user favourites, otherwise false
def check_favourite(region, player_name):
    api_url = "https://gvjidvxif1.execute-api.us-east-1.amazonaws.com/prod/favourite?region=" + region
    myobj = {"email": session["email"], "player_name": player_name}
    headers = {"x-api-key": users_key}
    get_response = requests.get(api_url, json=myobj, headers=headers)
    if get_response.status_code == 200:
        return True
    else:
        return False


# Get oc1 and na favourites and add together in a list
def get_favourites_list():
    favourites_oce = query_favourites("OC1")
    favourites_na = query_favourites("NA1")
    favourites_details = []
    if favourites_oce:
        for favourite in favourites_oce:
            player_info = get_player_info("OC1", favourite["player_name"])
            fav = Favourite(favourite["player_name"], "OC1", player_info["profileIconId"], favourite["time_added"])
            favourites_details.append(fav)
    if favourites_na:
        for favourite in favourites_na:
            player_info = get_player_info("NA1", favourite["player_name"])
            fav = Favourite(favourite["player_name"], "NA1", player_info["profileIconId"], favourite["time_added"])
            favourites_details.append(fav)
    return favourites_details


# ----------------------
# SESSIONS
# ----------------------

# Make a new user session
def make_session(email, username):
    session["email"] = email
    session["username"] = username


# Check if a user session is in progress
def check_session():
    if "email" in session:
        return True
    else:
        return False


# Terminate current user session
def remove_session():
    session.pop("email", None)


# ----------------------
# LOL DATA DRAGON
# ----------------------

# Reurn data for specific champion
def get_champion_data(champion_name):
    api_url = "https://ddragon.leagueoflegends.com/cdn/12.20.1/data/en_US/champion/" + champion_name + ".json"
    response = requests.get(api_url)
    champion = response.json()
    return champion["data"][champion_name]


# Returns different types of game modes available
def get_queue_types():
    api_url = "https://static.developer.riotgames.com/docs/lol/queues.json"
    response = requests.get(api_url)
    queue_types = response.json()
    return queue_types


# ----------------------
# LOL API
# ----------------------

# Return ranked leaderboard for a specific region
def get_leaderboard(region):
    api_url = "https://" + region + ".api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5?api_key=" + api_key
    while True:
        response = requests.get(api_url)
        if response.status_code == 429:
            time.sleep(10)
            continue
        if response.status_code == 200:
            leaderboard = response.json()
            return leaderboard


# Return player ranked information
def get_player_rank_info(search_region, encrypted_summoner_id):
    api_url = "https://" + search_region + ".api.riotgames.com/lol/league/v4/entries/by-summoner/" + encrypted_summoner_id + "?api_key=" + api_key
    while True:
        response = requests.get(api_url)
        if response.status_code == 429:
            time.sleep(10)
            continue
        if response.status_code == 200:
            player_rank_info = response.json()
            return player_rank_info


# Return player general information
def get_player_info(search_region, search_player_name):
    api_url = "https://" + search_region + ".api.riotgames.com/lol/summoner/v4/summoners/by-name/" + search_player_name + "?api_key=" + api_key
    while True:
        response = requests.get(api_url)
        if response.status_code == 429:
            time.sleep(10)
            continue
        if response.status_code == 200:
            player_info = response.json()
            return player_info
        else:
            return


# Returns match history inormation for a player's last 10 games
async def get_match_history(search_region, puuid):
    match_ids = get_match_ids(search_region, puuid)
    async with aiohttp.ClientSession() as sess:
        tasks = []
        # 10 Riot API calls are made here, async is used to speed up process.
        for match_id in match_ids:
            task = asyncio.ensure_future(get_match_info(sess, match_id, search_region))
            tasks.append(task)
        match_history = await asyncio.gather(*tasks)
        return match_history


# Returns list of match ids for a player
def get_match_ids(search_region, puuid):
    region = region_converter(search_region)
    # Only showing past 10 matches because of Riot API rate limiting.
    api_url = "https://" + region + ".api.riotgames.com/lol/match/v5/matches/by-puuid/" + puuid + "/ids?start=0&count=10&api_key=" + api_key
    while True:
        response = requests.get(api_url)
        if response.status_code == 429:
            time.sleep(10)
            continue
        if response.status_code == 200:
            player_matches = response.json()
            return player_matches


# Returns information for a match based on a match id
async def get_match_info(sess, match_id, search_region):
    region = region_converter(search_region)
    api_url = "https://" + region + ".api.riotgames.com/lol/match/v5/matches/" + match_id + "?api_key=" + api_key
    while True:
        async with sess.get(api_url, ssl_context=ssl_context) as response:
            if response.status == 429:
                time.sleep(10)
                continue
            if response.status == 200:
                match_info = await response.json()
                return match_info


# ----------------------
# OTHER LOL FUNCTIONS
# ----------------------

# Some APIs are older than others and require region in a different format,
# this function is used to convert region to appropriate format
def region_converter(search_region):
    region = None
    if search_region == "OC1":
        region = "SEA"
    if search_region == "NA1":
        region = "AMERICAS"
    return region


# Calculates win rate for recent match history
def get_win_rate(match_history, player_info):
    win = 0
    loss = 0
    for match in match_history:
        n = match["metadata"]["participants"].index(player_info["puuid"])
        if match["info"]["participants"][n]["win"]:
            win += 1
        else:
            loss += 1
    win_rate = {'win': win, 'loss': loss}
    return win_rate


# Calculates role stats for recent match history
def get_role_stats(match_history, player_info):
    middle = 0
    top = 0
    jungle = 0
    bottom = 0
    support = 0
    for match in match_history:
        n = match["metadata"]["participants"].index(player_info["puuid"])
        if match["info"]["participants"][n]["teamPosition"] == "MIDDLE":
            middle += 1
        elif match["info"]["participants"][n]["teamPosition"] == "TOP":
            top += 1
        elif match["info"]["participants"][n]["teamPosition"] == "JUNGLE":
            jungle += 1
        elif match["info"]["participants"][n]["teamPosition"] == "BOTTOM":
            bottom += 1
        elif match["info"]["participants"][n]["teamPosition"] == "UTILITY":
            support += 1
        else:
            middle += 1
    role_stats = {'middle': middle, 'top': top, 'jungle': jungle, 'bottom': bottom, 'support': support}
    return role_stats


# ----------------------
# CLOUDSEARCH API
# ----------------------

# Put user input in URL format, call Cloud Search API, return results
def get_champions(term, champion_class, difficulty, sort):
    difficulty_filter = ""
    class_filter = ""
    # Return alll champions if no term is entered , else search the term
    if term == "all" or "":
        query = "matchall&q.parser=structured"
    else:
        query = term
    # If class and difficult is set to all, filter all
    if champion_class == "all" and difficulty == "all":
        query_filter = "matchall"
    else:
        # If class not set to all, filter by the class specified
        if champion_class != "all":
            class_filter = " tags: '" + champion_class + "'"
        # If difficult not all, filter by difficulty specified
        if difficulty != "all":
            if difficulty == "easy":
                difficulty_filter = " (or difficulty: 0 difficulty: 1 difficulty: 2 difficulty: 3)"
            elif difficulty == "medium":
                difficulty_filter = " (or difficulty: 4 difficulty: 5 difficulty: 6 difficulty: 7)"
            elif difficulty == "hard":
                difficulty_filter = " (or difficulty: 8 difficulty: 9 difficulty: 10)"
        query_filter = "(and" + class_filter + difficulty_filter + ")"
    # Make the URL
    url = cloud_search_url + "?q=" + query + "&q.options={'fields':['name']}&size=200&sort=name " + sort + "&fq=" + query_filter
    # Call CloudSearch API
    response = requests.get(url)
    search_results = response.json()
    return search_results["hits"]


# ----------------------
# MAIN
# ----------------------

if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8080, debug=True)
