"""API路由模块"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# 导入路由
from app.routes import events

