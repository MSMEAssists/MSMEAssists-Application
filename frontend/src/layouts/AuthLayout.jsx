import Brand from "../components/ui/Brand";

export default function AuthLayout({ heroEyebrow, heroTitle, heroLede, heroFooter, children }) {
  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[1.05fr_1fr]">
      <div className="relative flex min-h-[320px] flex-col justify-between overflow-hidden bg-gradient-to-br from-navy-950 via-navy-900 to-navy-800 px-8 py-12 text-white sm:px-14">
        <div className="pointer-events-none absolute inset-0 opacity-40">
          <div className="absolute -left-16 -top-16 h-72 w-72 rounded-full bg-teal-500/20 blur-3xl" />
        </div>

        <div className="relative z-10">
          <Brand onDark size={34} />
        </div>

        <div className="relative z-10 mt-8 max-w-md">
          <div className="mb-4 flex items-center gap-2 font-data text-xs uppercase tracking-wider text-teal-300">
            <span className="h-px w-4 bg-teal-300" /> {heroEyebrow}
          </div>
          <h1 className="mb-4 font-display text-3xl font-semibold leading-tight text-white sm:text-[34px]">
            {heroTitle}
          </h1>
          <p className="text-[15.5px] leading-relaxed text-teal-100/70">{heroLede}</p>
        </div>

        <div className="relative z-10 mt-8 flex items-center gap-2.5 font-data text-xs text-teal-100/70">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 2L4 5v6c0 5 3.4 9 8 11 4.6-2 8-6 8-11V5l-8-3z"
              stroke="#5FCFC4"
              strokeWidth="1.6"
            />
          </svg>
          {heroFooter}
        </div>
      </div>

      <div className="flex items-center justify-center bg-bg-raised px-6 py-12 sm:px-8">
        <div className="w-full max-w-[400px]">
          <div className="mb-7 flex md:hidden">
            <Brand size={30} />
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
