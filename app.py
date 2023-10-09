import json
import openai
from flask import Flask, redirect, render_template, request, url_for
import plivo

app = Flask(__name__)
openai.api_key = "<openai_api_key>"

groups = []

@app.route('/get_numbers')
def get_numbers():
    return render_template('get_numbers.html')

@app.route('/submit', methods=['POST'])
def submit():
    global groups

    group_names = request.form.getlist('group_name[]')

    for group_name in group_names:
        names = request.form.getlist(f'name[][{group_names.index(group_name)}]')
        phones = request.form.getlist(f'phone[][{group_names.index(group_name)}]')

        # Combine names and phones into a list of dictionaries
        contacts = [{"name": name, "phone": phone} for name, phone in zip(names, phones)]

        # Check if the group already exists
        group_exists = False
        for group in groups:
            if group['group_name'] == group_name:
                group_exists = True
                group['contacts'].extend(contacts)
                break

        # If the group doesn't exist, create a new group
        if not group_exists:
            group = {"group_name": group_name, "contacts": contacts}
            groups.append(group)

    # Save all groups as a single JSON file
    with open("groups.json", "w") as json_file:
        json.dump(groups, json_file, indent=4)

    return redirect(url_for('index'))

def load_groups():
    try:
        with open("groups.json", "r") as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        return []

@app.route("/", methods=("GET", "POST"))
def index():
    groups = load_groups()  # Load groups from the JSON file
    group_names = [group["group_name"] for group in groups]  # Extract group names

    if request.method == "POST":
        topic = request.form["topic"]
        mood = request.form["mood"]
        reciever = request.form.get("reciever", False)
        length = request.form["length"]
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_prompt(topic, mood, reciever, length),
            temperature=0.5,
            max_tokens=1024
        )
        selected_group = request.form.get('group')  # Retrieve the selected group
        return render_template("index.html", group_names=group_names, result=response.choices[0].text, selected_group=selected_group)

    result = request.args.get("result")
    return render_template("index.html", group_names=group_names, result=result, selected_group=None)

@app.route("/send", methods=["POST"])
def send_message():
    auth_id = "plivo_api_key"
    auth_token = "plivo_password"

    plivo_client = plivo.RestClient(auth_id, auth_token)

    src_phone = "+917306181750"
    if request.method == "POST":
        message = request.form["message"]
        selected_group = request.form["group"]

        groups = load_groups()  # Load groups from the JSON file
        for group in groups:
            if(group["group_name"]==selected_group):
                dest_phone=""
                for contact in group["contacts"]:
                    if len(dest_phone)==0:
                        dest_phone+=f'+91{contact["phone"]}'
                    else:
                        dest_phone+=f'<+91{contact["phone"]}'
                response = plivo_client.messages.create(
                    src=src_phone,
                    dst=dest_phone,
                    text=message
                )
                print(dest_phone)
                print(response)
                return "Message sent successfully to {} group!".format(selected_group)

    return redirect(url_for("index"))


def generate_prompt(topic, mood, reciever, length):
    return """Take the prompt given below and write an SMS message to my {}:
    Topic of the message will be:{}
    Type of SMS: {}
    length: {}""".format(
        reciever, 
        topic.capitalize(), 
        mood, 
        length
    )

if __name__ == '__main__':
    app.debug = True
    app.run()
