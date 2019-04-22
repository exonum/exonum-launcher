from typing import Optional

from flask import Flask, render_template, request
import os
from .messages import get_constructor_data_classes, get_signed_tx
from .utils import load_config, gen_keypair
from .client import ExonumClient

file_folder = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(file_folder, "/templates")
app = Flask(__name__)

constructor_data_classes = get_constructor_data_classes()

exonum_client: Optional[ExonumClient] = None
pk, sk = gen_keypair()


@app.route("/")
def hello() -> str:
    res = ""
    messages = []

    for cd in constructor_data_classes:
        message = {}
        message["name"] = cd.__name__
        message["fields"] = []
        cd_obj = cd()

        for field in cd_obj.DESCRIPTOR.fields:
            message["fields"].append(field.name)

        messages.append(message)

    return render_template("index.html", messages=messages)


@app.route("/send", methods=['POST'])
def send() -> str:
    if not exonum_client:
        return "Exonum client wasn't configured. Consider running through `python -m exonum-launcher`"

    artifact_name = request.form['artifact_name']
    artifact_version = request.form['artifact_version']
    instance_name = request.form['instance_name']

    constructor_data = {}
    for field in request.form:
        if field.startswith('init_'):
            field_name = field[len('init_'):]
            constructor_data[field_name] = request.form[field]

    transaction = {
        'artifact_spec': {
            'name': artifact_name,
            'version': artifact_version
        },
        'instance_name': instance_name,
        'constructor_data': constructor_data,
    }

    signed_tx = get_signed_tx(pk, sk, transaction)

    response = exonum_client.send_raw_tx(signed_tx.SerializeToString())

    if response.get('error'):
        result = "Request errored. Check if exonum instance running and config is correct. Error: {}"

        return result.format(response['error'])

    return "Success. Exonum response: {}".format(response)


def main(args) -> None:
    data = load_config(args.input)
    transactions = data["transactions"]
    exonum_cfg = data["exonum"]
    client = ExonumClient(exonum_cfg["hostname"], exonum_cfg["public_api_port"], exonum_cfg["ssl"])

    app.run()
