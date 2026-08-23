export default function Switch({ checked, onChange, label, description, disabled }) {
  return (
    <div className="mb-2.5 flex items-start justify-between gap-4 rounded-md border-[1.5px] border-border px-4 py-3.5 transition-colors hover:border-border-strong">
      <div>
        <b className="block text-[13.5px] text-ink-900">{label}</b>
        {description && <span className="text-xs text-ink-500">{description}</span>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className="switch-track flex-shrink-0"
        data-checked={checked}
      >
        <span className="switch-knob" />
      </button>
    </div>
  );
}
