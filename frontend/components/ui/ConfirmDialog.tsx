"use client";

import { Modal } from "./Modal";
import { Button } from "./Button";

type Props = {
  aberto: boolean;
  titulo: string;
  mensagem: string;
  confirmando?: boolean;
  variantePerigo?: boolean;
  onConfirmar: () => void;
  onCancelar: () => void;
};

export function ConfirmDialog({
  aberto,
  titulo,
  mensagem,
  confirmando,
  variantePerigo = true,
  onConfirmar,
  onCancelar,
}: Props) {
  return (
    <Modal aberto={aberto} titulo={titulo} onFechar={onCancelar}>
      <p className="mb-5 text-sm text-foreground">{mensagem}</p>
      <div className="flex justify-end gap-2">
        <Button variante="secundaria" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button
          variante={variantePerigo ? "perigo" : "primaria"}
          onClick={onConfirmar}
          carregando={confirmando}
        >
          Confirmar
        </Button>
      </div>
    </Modal>
  );
}
