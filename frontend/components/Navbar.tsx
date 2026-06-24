"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Users, Gavel, Zap, Newspaper } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { name: "Match Strategy", path: "/selection", icon: <Users className="w-4 h-4" /> },
    { name: "Auction Strategy", path: "/auction", icon: <Gavel className="w-4 h-4" /> },
    { name: "Player Analysis", path: "/lab", icon: <Zap className="w-4 h-4" />},
    { name: "News Feed", path: "/news", icon: <Newspaper className="w-4 h-4" /> },
  ];

  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <Activity className="text-blue-500 w-6 h-6" />
          <span className="text-xl font-bold text-white tracking-tight">CrickAI</span>
        </Link>
        
        <div className="flex space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 hidden md:flex">
          {navLinks.map((link) => {
            const isActive = pathname.startsWith(link.path);
            return (
              <Link 
                key={link.path} 
                href={link.path}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${isActive ? "bg-blue-600 text-white shadow-md" : "text-slate-400 hover:text-slate-200"}`}
              >
                {link.icon} {link.name}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}