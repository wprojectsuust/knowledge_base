/** Размытые цветные пятна, которые медленно плавают за всем интерфейсом. Чистый CSS, без JS. */
export function AnimatedBackground() {
  return (
    <div className="bg-blobs" aria-hidden>
      <span className="blob blob-1" />
      <span className="blob blob-2" />
      <span className="blob blob-3" />
      <span className="blob blob-4" />
    </div>
  );
}
