import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Field, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";

export function Documentos() {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [titulo, setTitulo] = useState("");
  const [contratoId, setContratoId] = useState("");
  const [drag, setDrag] = useState(false);

  const contratos = useQuery({ queryKey: ["contratos", "doc"], queryFn: () => api.listarContratos({ limit: 200 }) });

  const subir = useMutation({
    mutationFn: () => api.subirDocumento(file!, { contrato_id: contratoId ? Number(contratoId) : undefined, titulo: titulo || undefined }),
    onSuccess: () => { toast.success("Documento subido. Se procesará en background (parse/chunk/embed)."); setFile(null); setTitulo(""); setContratoId(""); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error al subir."),
  });

  return (
    <>
      <PageHeader title="Documentos" subtitle="Sube documentos; se versionan y se indexan para la búsqueda por contenido." />
      <div className="mx-auto max-w-[640px]">
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-10 transition-colors ${drag ? "border-primary bg-primary-container/10" : "border-outline-variant bg-surface-container-low"}`}
        >
          <Icon name="cloud_upload" className="text-[48px] text-primary" />
          {file ? (
            <p className="font-title-sm text-title-sm text-on-surface">{file.name} <span className="font-data-mono text-data-mono text-outline">({(file.size / 1024).toFixed(0)} KB)</span></p>
          ) : (
            <>
              <p className="font-title-sm text-title-sm text-on-surface">Arrastra un archivo o haz clic</p>
              <p className="font-body-sm text-body-sm text-secondary">PDF, DOCX, TXT…</p>
            </>
          )}
          <input ref={inputRef} type="file" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>

        <div className="mt-stack-relaxed flex flex-col gap-3">
          <Field label="Título (opcional)"><input className="input" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Nombre descriptivo" /></Field>
          <Field label="Vincular a contrato (opcional)">
            <select className="input" value={contratoId} onChange={(e) => setContratoId(e.target.value)}>
              <option value="">— Sin vincular —</option>
              {contratos.data?.map((c) => <option key={c.id} value={c.id}>{c.numero ?? `#${c.id}`} · {c.titulo}</option>)}
            </select>
          </Field>
          <button className="btn-primary self-start" disabled={!file || subir.isPending} onClick={() => subir.mutate()}>
            {subir.isPending ? <><Spinner /> Subiendo…</> : <><Icon name="upload" className="text-[18px]" /> Subir documento</>}
          </button>
        </div>
      </div>
    </>
  );
}
