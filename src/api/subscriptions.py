import stripe
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sympy import pprint

router = APIRouter()


@router.get("/{subscription_id}/cancel", response_class=HTMLResponse)
async def cancel_subscription(
        subscription_id: str
):
    return '''<!DOCTYPE html>
<html lang="en" style="height: 100%;">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Ulu AI</title>
    <style>
        #container {
            display: flex;
            height: 100%;
            justify-content: center;
            align-items: anchor-center;">
        }
        #cancel_button {
            border: none;
            outline: none;
            background: #d74242;
            padding: 20px;
            border-radius: 10px;
            color: white;
            cursor: pointer;
        }
        #cancel_button:disabled {
            background: gray;
            cursor: default;
        }
    </style>
  </head>
  <body style="height: 100%;">
    <div id="container">
        <button id="cancel_button" onclick="cancel_subscription()">Unsubscribe</button>
        <p id="cancel_text" style="display: none;">Subscription canceled!</p>
    </div>
    <script>
    function cancel_subscription() {
        document.getElementById('cancel_button').disabled = true;
        fetch("/api/v1/payments/subscriptions/'''+subscription_id+'''/cancel", {method: "POST"})
        .then((response) => response.json())
        .then((json) => {
            document.getElementById('cancel_button').style.display = 'none';
            document.getElementById('cancel_text').style.display = 'flex';
        });
    }
    </script>
  </body>
</html>'''
