type Props = {
  className?: string;
};

export function Logo({ className = "h-7 w-7" }: Props) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="ARIABLE logo"
    >
      <defs>
        <linearGradient id="ariable-grad" x1="0" y1="0" x2="32" y2="32">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#6366f1" />
        </linearGradient>
      </defs>
      <path
        d="M16 2 L30 28 H2 Z"
        fill="url(#ariable-grad)"
        opacity="0.95"
      />
      <path
        d="M16 12 L22 24 H10 Z"
        fill="#09090b"
      />
    </svg>
  );
}
