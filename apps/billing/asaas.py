import requests
from uuid import uuid4
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


class AsaasPixSubscription(AsaasBase):

    def create_subscription(self, customer_id, value, cycle, next_due_date, description):
        """ https://docs.asaas.com/reference/criar-uma-autorizacao-pix-automatico """
        return self.send_request(
            path="pix/automatic/authorizations",
            method="POST",
            body={
                "customerId": customer_id,
                "contractId": uuid4().hex,
                "value": float(value),
                "frequency": cycle,
                "startDate": next_due_date,
                "description": description,
                "immediateQrCode": {
                    "expirationSeconds": 3600,
                    "originalValue": float(value),
                    "description": description,
                },
            },
        )


class AsaasCreditCardSubscription(AsaasBase):

    def get_subscription(self, subscription_id):
        """ https://docs.asaas.com/reference/recuperar-uma-unica-assinatura """
        return self.send_request(
            path=f"subscriptions/{subscription_id}",
            method="GET",
        )

    def create_subscription(self, customer_id, value, cycle, next_due_date, description, credit_card, credit_card_holder_info):
        """ https://docs.asaas.com/reference/criar-assinatura-com-cartao-de-credito """
        return self.send_request(
            path="subscriptions",
            method="POST",
            body={
                "customer": customer_id,
                "value": float(value),
                "cycle": cycle,
                "nextDueDate": next_due_date,
                "description": description,
                "billingType": "CREDIT_CARD",
                "creditCard": credit_card,
                "creditCardHolderInfo": credit_card_holder_info,
            },
        )

    def update_subscription(self, subscription_id, status=None, value=None, cycle=None, next_due_date=None, description=None, updatePendingPayments=None):
        """ https://docs.asaas.com/reference/atualizar-assinatura-existente """
        body = {
            "status": status,
            "value": float(value) if value is not None else None,
            "cycle": cycle,
            "nextDueDate": next_due_date,
            "description": description,
            "updatePendingPayments": updatePendingPayments,
        }
        body = {key: value for key, value in body.items() if value not in [None, "", [], {}]}

        return self.send_request(
            path=f"subscriptions/{subscription_id}",
            method="PUT",
            body=body,
        )

    def delete_subscription(self, subscription_id):
        """ https://docs.asaas.com/reference/remover-assinatura """
        return self.send_request(
            path=f"subscriptions/{subscription_id}",
            method="DELETE",
        )

    def update_credit_card(self, subscription_id, credit_card, credit_card_holder_info):
        """ https://docs.asaas.com/reference/atualizar-cartao-de-credito-assinatura """
        return self.send_request(
            path=f"subscriptions/{subscription_id}/creditCard",
            method="PUT",
            body={
                "creditCard": credit_card,
                "creditCardHolderInfo": credit_card_holder_info,
            },
        )


class AsaasPayment(AsaasBase):

    def list_payments(self, customer_id):
        """ https://docs.asaas.com/reference/listar-cobrancas """
        return self.send_request(
            path=f"payments?customer={customer_id}",
            method="GET",
        )

    def get_payment(self, payment_id):
        """ https://docs.asaas.com/reference/recuperar-uma-unica-cobranca """
        return self.send_request(
            path=f"payments/{payment_id}",
            method="GET",
        )

    def create_payment(self, customer_id, value, due_date, description=None, external_reference=None, credit_card=None, credit_card_holder_info=None):
        """ https://docs.asaas.com/reference/criar-nova-cobranca """
        body = {
            "customer": customer_id,
            "value": float(value),
            "dueDate": due_date,
            "description": description,
            "externalReference": external_reference,
            "billingType": "CREDIT_CARD",
            "creditCard": credit_card,
            "creditCardHolderInfo": credit_card_holder_info,
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
