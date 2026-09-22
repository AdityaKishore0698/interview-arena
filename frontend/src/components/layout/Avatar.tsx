'use client';

/* eslint-disable @next/next/no-img-element */
// A user-uploaded avatar can be a data: URI (client-resized upload) or an
// external https:// URL — next/image can't optimize either sensibly here
// (data: URIs aren't supported, and an arbitrary external host isn't
// allowlisted), so a plain <img> is the right tool.

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase();
}

interface AvatarProps {
  name: string;
  src?: string | null;
  size?: number;
  className?: string;
}

export function Avatar({ name, src, size = 40, className = '' }: AvatarProps) {
  const dim = { width: size, height: size };
  if (src) {
    return (
      <img
        src={src}
        alt={`${name}'s profile photo`}
        style={dim}
        className={`shrink-0 rounded-full object-cover ${className}`}
      />
    );
  }
  return (
    <div
      style={{ ...dim, fontSize: size * 0.4 }}
      className={`flex shrink-0 items-center justify-center rounded-full bg-primary-gradient font-semibold text-white ${className}`}
    >
      {initials(name)}
    </div>
  );
}
