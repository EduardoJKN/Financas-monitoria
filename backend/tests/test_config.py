"""Testes da configuração via variáveis de ambiente (CORS multi-origem)."""

from app.core import config


def test_origens_permitidas_usa_localhost_3000_por_padrao(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    assert config.origens_permitidas() == ["http://localhost:3000"]


def test_origens_permitidas_aceita_uma_unica_origem(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://app.vercel.app")
    assert config.origens_permitidas() == ["https://app.vercel.app"]


def test_origens_permitidas_remove_barra_final(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://app.vercel.app/")
    assert config.origens_permitidas() == ["https://app.vercel.app"]


def test_origens_permitidas_aceita_multiplas_origens_separadas_por_virgula(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://app.vercel.app, http://localhost:3000")
    assert config.origens_permitidas() == ["https://app.vercel.app", "http://localhost:3000"]


def test_origens_permitidas_ignora_entradas_vazias(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://app.vercel.app,,")
    assert config.origens_permitidas() == ["https://app.vercel.app"]
