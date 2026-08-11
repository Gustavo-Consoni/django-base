import requests
from urllib.parse import urlencode, urljoin
from django.conf import settings


class AsaasBase:

    def __init__(self):
        self.API_KEY = settings.ASAAS_API_KEY
        self.BASE_URL = settings.ASAAS_BASE_URL

    def send_request(self, path, method="GET", query_params={}, body={}):
        url = self.mount_url(path, query_params)
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access_token": self.API_KEY,
        }

        match method.upper():
            case "GET":
                response = requests.get(url=url, headers=headers)
            case "POST":
                response = requests.post(url=url, headers=headers, json=body)
            case "PUT":
                response = requests.put(url=url, headers=headers, json=body)
            case "DELETE":
                response = requests.delete(url=url, headers=headers)

        response.raise_for_status()
        return response.json()

    def mount_url(self, path, query_params={}):
        parameters = urlencode(query_params)

        url = urljoin(self.BASE_URL, path)
        if parameters:
            url += "?" + parameters

        return url


class AsaasCustomer(AsaasBase):

    def get_customer(self, customer_id):
        """ https://docs.asaas.com/reference/recuperar-um-unico-cliente """
        return self.send_request(
            path=f"customers/{customer_id}",
            method="GET",
        )

    def create_customer(self, name, cpf_cnpj, email=None, mobile_phone=None, postal_code=None, address_number=None, complement=None):
        """ https://docs.asaas.com/reference/criar-novo-cliente """
        return self.send_request(
            path="customers",
            method="POST",
            body={
                "name": name,
                "cpfCnpj": cpf_cnpj,
                "email": email,
                "mobilePhone": mobile_phone,
                "postalCode": postal_code,
                "addressNumber": address_number,
                "complement": complement,
                "notificationDisabled": True,
            },
        )

    def update_customer(self, customer_id, name=None, cpf_cnpj=None, email=None, mobile_phone=None, postal_code=None, address_number=None, complement=None):
        """ https://docs.asaas.com/reference/atualizar-cliente-existente """
        body = {
            "name": name,
            "cpfCnpj": cpf_cnpj,
            "email": email,
            "mobilePhone": mobile_phone,
            "postalCode": postal_code,
            "addressNumber": address_number,
            "complement": complement,
        }
        body = {key: value for key, value in body.items() if value not in [None, "", [], {}]}

        return self.send_request(
            path=f"customers/{customer_id}",
            method="PUT",
            body=body,
        )

    def delete_customer(self, customer_id):
        """ https://docs.asaas.com/reference/remover-cliente """
        return self.send_request(
            path=f"customers/{customer_id}",
            method="DELETE",
        )


class AsaasSubscription(AsaasBase):

    def create_pix_subscription(self, contract_id, customer_id, first_value, recurring_value, cycle, due_date, description, payment_creation_mode="SUBSCRIPTION"):
        """ https://docs.asaas.com/reference/criar-uma-autorizacao-pix-automatico """
        return self.send_request(
            path="pix/automatic/authorizations",
            method="POST",
            body={
                "contractId": contract_id,
                "customerId": customer_id,
                "value": float(recurring_value),
                "frequency": cycle,
                "startDate": due_date,
                "description": description,
                "immediateQrCode": {
                    "expirationSeconds": 3600,
                    "originalValue": float(first_value),
                    "description": description,
                },
                "paymentCreationMode": payment_creation_mode,
            },
        )

    def delete_pix_subscription(self, pix_authorization_id):
        """ https://docs.asaas.com/reference/cancelar-uma-autorizacao-pix-automatico """
        return self.send_request(
            path=f"pix/automatic/authorizations/{pix_authorization_id}",
            method="DELETE",
        )

    def create_credit_card_subscription(self, customer_id, value, next_due_date, description, external_reference=None, credit_card=None, credit_card_holder_info=None, credit_card_token=None):
        """ https://docs.asaas.com/reference/criar-nova-assinatura """
        body = {
            "customer": customer_id,
            "billingType": "CREDIT_CARD",
            "value": float(value),
            "nextDueDate": next_due_date,
            "description": description,
            "externalReference": external_reference,
            "creditCard": credit_card,
            "creditCardHolderInfo": credit_card_holder_info,
            "creditCardToken": credit_card_token,
        }
        body = {key: value for key, value in body.items() if value not in [None, "", [], {}]}

        return self.send_request(
            path=f"subscriptions",
            method="POST",
            body=body,
        )

    def delete_credit_card_subscription(self, subscription_id):
        """ https://docs.asaas.com/reference/remover-assinatura """
        return self.send_request(
            path=f"subscriptions/{subscription_id}",
            method="DELETE",
        )


class AsaasPayment(AsaasBase):

    def get_payment(self, payment_id):
        """ https://docs.asaas.com/reference/recuperar-uma-unica-cobranca """
        return self.send_request(
            path=f"payments/{payment_id}",
            method="GET",
        )

    def create_payment(self, customer_id, billing_type, value, due_date, description, external_reference=None, credit_card=None, credit_card_holder_info=None, credit_card_token=None, pix_authorization_id=None):
        """ https://docs.asaas.com/reference/criar-nova-cobranca """
        body = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": float(value),
            "dueDate": due_date,
            "description": description,
            "externalReference": external_reference,
            "creditCard": credit_card,
            "creditCardHolderInfo": credit_card_holder_info,
            "creditCardToken": credit_card_token,
            "pixAutomaticAuthorizationId": pix_authorization_id,
        }
        body = {key: value for key, value in body.items() if value not in [None, "", [], {}]}

        return self.send_request(
            path=f"payments",
            method="POST",
            body=body,
        )

    def delete_payment(self, payment_id):
        """ https://docs.asaas.com/reference/excluir-cobranca """
        return self.send_request(
            path=f"payments/{payment_id}",
            method="DELETE",
        )

    def refund_payment(self, payment_id):
        """ https://docs.asaas.com/reference/estornar-cobranca """
        return self.send_request(
            path=f"payments/{payment_id}/refund",
            method="POST",
        )

    def tokenize_credit_card(self, customer_id, credit_card, credit_card_holder_info):
        """ https://docs.asaas.com/reference/tokenizacao-de-cartao-de-credito """
        return self.send_request(
            path=f"creditCard/tokenizeCreditCard",
            method="POST",
            body={
                "customer": customer_id,
                "creditCard": credit_card,
                "creditCardHolderInfo": credit_card_holder_info,
            },
        )
