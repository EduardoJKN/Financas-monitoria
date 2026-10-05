from datetime import date
from decimal import Decimal

import pytest

from src import ofx

_OFX_AMOSTRA = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20260315120000
<LANGUAGE>POR
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>BRL
<BANKACCTFROM>
<BANKID>0001
<ACCTID>12345-6
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260301
<DTEND>20260331
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260302120000
<TRNAMT>3000.00
<FITID>1001
<MEMO>SALARIO EMPRESA XYZ
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260303120000
<TRNAMT>-45.90
<FITID>1002
<MEMO>IFOOD *DELIVERY
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>5000.00
<DTASOF>20260331120000
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


def test_ler_transacoes_ofx_classifica_por_sinal():
    linhas = ofx.ler_transacoes_ofx(_OFX_AMOSTRA)
    assert len(linhas) == 2

    receita = next(l for l in linhas if l["descricao"] == "SALARIO EMPRESA XYZ")
    assert receita["tipo"] == "receita"
    assert receita["valor"] == Decimal("3000.00")
    assert receita["data"] == date(2026, 3, 2)
    assert isinstance(receita["valor"], Decimal)

    despesa = next(l for l in linhas if l["descricao"] == "IFOOD *DELIVERY")
    assert despesa["tipo"] == "despesa"
    assert despesa["valor"] == Decimal("45.90")


def test_ler_transacoes_ofx_vazio_levanta_erro():
    with pytest.raises(ValueError):
        ofx.ler_transacoes_ofx(b"")


def test_ler_transacoes_ofx_invalido_levanta_erro_amigavel():
    with pytest.raises(ValueError):
        ofx.ler_transacoes_ofx(b"isso nao e um arquivo ofx valido")
