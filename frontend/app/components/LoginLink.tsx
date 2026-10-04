"use client";

import { useRouter } from "next/navigation";

export default function LoginLink({ href, className, children, style }: { href: string, className?: string, children: React.ReactNode, style?: React.CSSProperties }) {
  const router = useRouter();

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    // Start exit transition on the landing page content
    const content = document.getElementById("landing-content");
    if (content) {
      content.classList.add("animate-out");
      setTimeout(() => {
        router.push(href);
      }, 300); // match CSS duration
    } else {
      router.push(href);
    }
  };

  return (
    <a href={href} className={className} style={style} onClick={handleClick}>
      {children}
    </a>
  );
}
