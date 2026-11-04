"""Gera os ícones PWA do Economia UaU a partir de um único desenho vetorial
simples (Pillow), em vez do placeholder de texto "UaU" anterior.

Símbolo: quadrado arredondado na cor da marca (--primaria: #2563eb) com uma
linha ascendente (sparkline) em branco — referência a crescimento financeiro
sem usar um cifrão genérico. Um ponto verde (--receita-texto) marca o topo da
linha, reforçando a semântica de "resultado positivo" já usada no resto do
app (Parte 29: cor sempre acompanhada de forma, nunca só decorativa).

Reexecutar após qualquer mudança de marca: `python scripts/gerar_icones.py`.
"""

from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "public" / "icons"

COR_FUNDO = (37, 99, 235)  # --primaria
COR_TRACO = (255, 255, 255)
COR_PONTO = (74, 222, 128)  # --receita-texto (dark mode), bom contraste sobre o azul


def _desenhar_base(tamanho: int) -> Image.Image:
    escala = tamanho / 512
    img = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    raio = int(112 * escala)
    draw.rounded_rectangle([0, 0, tamanho - 1, tamanho - 1], radius=raio, fill=COR_FUNDO)

    pontos = [
        (96 * escala, 332 * escala),
        (206 * escala, 240 * escala),
        (278 * escala, 300 * escala),
        (416 * escala, 150 * escala),
    ]
    largura_traco = max(1, int(26 * escala))
    draw.line(pontos, fill=COR_TRACO, width=largura_traco, joint="curve")

    raio_ponta = int(largura_traco * 0.9)
    for extremidade in (pontos[0], pontos[-1]):
        x, y = extremidade
        draw.ellipse(
            [x - largura_traco / 2, y - largura_traco / 2, x + largura_traco / 2, y + largura_traco / 2],
            fill=COR_TRACO,
        )

    raio_destaque = int(34 * escala)
    x, y = pontos[-1]
    draw.ellipse(
        [x - raio_destaque, y - raio_destaque, x + raio_destaque, y + raio_destaque],
        fill=COR_PONTO,
    )

    return img


def gerar() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)

    _desenhar_base(512).save(DESTINO / "icon-512.png")
    _desenhar_base(192).save(DESTINO / "icon-192.png")

    # apple-touch-icon: sem transparência (iOS ignora alpha e mostra preto) —
    # compõe sobre fundo da própria cor de marca antes de salvar em RGB.
    apple = Image.new("RGB", (180, 180), COR_FUNDO)
    apple.paste(_desenhar_base(180), (0, 0), _desenhar_base(180))
    apple.save(DESTINO / "apple-touch-icon.png")

    # favicon multi-resolução a partir do mesmo desenho
    favicon_sizes = [16, 32, 48]
    favicons = [_desenhar_base(s) for s in favicon_sizes]
    favicons[0].save(
        RAIZ / "app" / "favicon.ico",
        format="ICO",
        sizes=[(s, s) for s in favicon_sizes],
        append_images=favicons[1:],
    )

    print(f"Ícones gerados em {DESTINO} e {RAIZ / 'app' / 'favicon.ico'}")


if __name__ == "__main__":
    gerar()
