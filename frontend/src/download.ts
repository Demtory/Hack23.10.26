/**
 * Скачивание Blob через временную ссылку.
 *
 * Ссылка обязательно добавляется в DOM: Firefox (и Zen) игнорируют click()
 * по отсоединённому якорю, из-за чего скачивание молча не начинается.
 * Возвращает object URL — вызывающий код решает, когда его освобождать.
 */
export function downloadBlob(blob: Blob, filename: string): string {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  return url;
}
