import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import time
import pandas as pd
import random
import json
import uuid
import requests
import base64
import re
import hashlib
import hmac
import secrets
import streamlit.components.v1 as components


# Daftar mata pelajaran dan program Bimbel Rumah Nazma
MAPEL_OPTIONS = [
    # PAUD / TK
    "Calistung", "Tematik TK", "Pendidikan Agama",

    # SD
    "Matematika SD", "Bahasa Indonesia SD", "IPAS SD",
    "Bahasa Inggris SD", "Pendidikan Pancasila SD", "PAI SD",
    "PJOK SD", "Seni Rupa SD", "Seni Musik SD", "Bahasa Arab SD",

    # SMP
    "Matematika SMP", "Bahasa Indonesia SMP", "Bahasa Inggris SMP",
