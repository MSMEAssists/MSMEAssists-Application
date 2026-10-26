import { FiExternalLink, FiFileText } from "react-icons/fi";

export default function ProvenanceList({ items }) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  return (
    <ul className="space-y-2">
      {items.map((item, idx) => (
        <ProvenanceRow key={item.chunk_id || `${item.statement}-${idx}`} item={item} />
      ))}
    </ul>
  );
}

export function ProvenanceRow({ item }) {
  if (!item) return null;

  return (
    <li className="rounded border border-border bg-surface-sunken px-3 py-2">
      <p className="text-xs leading-relaxed text-ink-700">{item.statement}</p>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-data text-[10px] text-ink-400">
        {item.page_number != null && (
          <span className="inline-flex items-center gap-0.5">
            <FiFileText size={10} /> Page {item.page_number}
          </span>
        )}
        {item.chunk_id && <span>Chunk {item.chunk_id}</span>}
        {item.source_organization && <span>{item.source_organization}</span>}
        {item.source_url && (
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-medium text-teal-600 hover:underline"
          >
            Official source <FiExternalLink size={10} />
          </a>
        )}
      </div>
    </li>
  );
}
