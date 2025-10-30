import os


# QuickBooks
CLIENT_ID = os.getenv("QBO_CLIENT_ID", "ABjSEkHu5eSVDUk43Yk6HPzMqTIqqwy1UIuvFvt46TJq7ekf3Q")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET", "3H8yukkptmxZ9JRgbuTgaOPmfbsm5HvSpfDDNQCN")
REFRESH_TOKEN = os.getenv("QBO_REFRESH_TOKEN", "RT1-197-H0-1770530586ocmam9e3g3805zjmjfmo")

REALM_ID = os.getenv("QBO_REALM_ID", "9130352047477256")
REDIRECT_URI = os.getenv("QBO_REDIRECT_URI", "https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl")
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
API_BASE_URL = "https://quickbooks.api.intuit.com"


# Rentman
REN_API_TOKEN = os.getenv("REN_API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w")
REN_BASE_URL = os.getenv("REN_BASE_URL", "https://api.rentman.net")


# QuickBooks Items (opzionali)
DEFAULT_QB_ITEM_ID = os.getenv("QBO_DEFAULT_ITEM_ID")
DEFAULT_QB_ITEM_NAME = os.getenv("QBO_DEFAULT_ITEM_NAME")
DEFAULT_QB_ITEM_EXPENSE_ACCOUNT_ID = os.getenv("QBO_DEFAULT_ITEM_EXPENSE_ACCOUNT_ID", "1")
DEFAULT_QB_ITEM_INCOME_ACCOUNT_ID = os.getenv("QBO_DEFAULT_ITEM_INCOME_ACCOUNT_ID")


