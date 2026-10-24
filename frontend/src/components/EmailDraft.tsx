import { useEffect, useState } from "react";
import type { EmailDraft } from "../types";
import { Dialog } from "./ui";

export function EmailDraftDialog({ draft, onClose }: { draft: EmailDraft; onClose: () => void }) {
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    setSubject(draft.subject);
    setBody(draft.body);
    setStatus(null);
  }, [draft]);

  async function copy() {
    const text = `Тема: ${subject}\n\n${body}`;
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Скопировано — можно вставить в письмо.");
    } catch {
      setStatus("Не удалось скопировать автоматически: выделите текст и скопируйте вручную.");
    }
  }

  const mailto = `mailto:${encodeURIComponent(draft.recipient)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <Dialog title={`Письмо клиенту · ${draft.situationLabel}`} onCancel={onClose}>
      <p>
        Черновик под ситуацию «{draft.situationLabel}». Проверьте суммы и сроки, поправьте тон под клиента
        и отправьте из своей почты.
      </p>
      <label className="field">
        <span>Кому</span>
        <input value={draft.recipient} readOnly />
      </label>
      <label className="field">
        <span>Тема</span>
        <input value={subject} onChange={(event) => setSubject(event.target.value)} />
      </label>
      <label className="field">
        <span>Текст письма</span>
        <textarea rows={14} value={body} onChange={(event) => setBody(event.target.value)} />
      </label>
      <div className="dialog-actions">
        <button className="button button--primary" autoFocus onClick={() => void copy()}>
          Скопировать
        </button>
        <a className="button" href={mailto}>
          Открыть в почте
        </a>
        <button className="button" onClick={onClose}>
          Закрыть
        </button>
      </div>
      {status ? <p role="status" className="muted">{status}</p> : null}
    </Dialog>
  );
}
