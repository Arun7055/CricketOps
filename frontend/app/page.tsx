import Link from "next/link";
import { Swords, Gavel, Activity, Radio, ArrowRight } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] text-center space-y-6 md:space-y-8 px-4 py-4 animate-in fade-in duration-700">
      
      {/* HERO BANNER */}
      <div className="space-y-3 max-w-4xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          v2.4 Multi-Agent Roster Engine Live
        </div>

        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white tracking-tight">
          Next-Generation <span className="bg-gradient-to-r from-blue-500 via-indigo-400 to-purple-500 bg-clip-text text-transparent">Cricket Intelligence</span>
        </h1>

        <p className="text-sm md:text-base text-slate-400 leading-relaxed max-w-2xl mx-auto">
          The ultimate multi-agent intelligence platform for professional sports franchises. 
          Leverage Groq AI and surface telemetry for tactical war rooms, auction mechanics, and live press intercepts.
        </p>
      </div>
      
      {/* 2x2 MASTER QUADRANT GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 w-full max-w-5xl text-left">
        
        {/* QUADRANT 1: THE WAR ROOM (BLUE) */}
        <Link href="/selection" className="group bg-slate-900/60 border border-slate-800 hover:border-blue-500/80 rounded-2xl p-5 md:p-6 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-xl hover:shadow-blue-500/10">
          <div className="absolute -top-4 -right-4 p-4 opacity-5 group-hover:opacity-10 transition-opacity pointer-events-none">
            <Swords className="w-28 h-28 text-blue-500" />
          </div>
          <div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-3 text-blue-400 group-hover:scale-110 transition-transform">
              <Swords className="w-5 h-5" />
            </div>
            <h3 className="text-lg md:text-xl font-black text-white mb-1 tracking-tight">Squad Analysis</h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-2">Check how the teams stack up against each other after auction.</p>
          </div>
          <span className="text-blue-400 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 group-hover:gap-2.5 transition-all mt-auto">
            Check it Out! <ArrowRight className="w-4 h-4"/>
          </span>
        </Link>

        {/* QUADRANT 2: AUCTION MECHANICS (PURPLE) */}
        <Link href="/auction" className="group bg-slate-900/60 border border-slate-800 hover:border-purple-500/80 rounded-2xl p-5 md:p-6 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-xl hover:shadow-purple-500/10">
          <div className="absolute -top-4 -right-4 p-4 opacity-5 group-hover:opacity-10 transition-opacity pointer-events-none">
            <Gavel className="w-28 h-28 text-purple-500" />
          </div>
          <div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-3 text-purple-400 group-hover:scale-110 transition-transform">
              <Gavel className="w-5 h-5" />
            </div>
            <h3 className="text-lg md:text-xl font-black text-white mb-1 tracking-tight">Auction Room</h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-2">Live bidding in auction room with friends.</p>
          </div>
          <span className="text-purple-400 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 group-hover:gap-2.5 transition-all mt-auto">
            Launch Room <ArrowRight className="w-4 h-4"/>
          </span>
        </Link>

        {/* QUADRANT 3: PLAYER LAB (EMERALD) */}
        <Link href="/lab" className="group bg-slate-900/60 border border-slate-800 hover:border-emerald-500/80 rounded-2xl p-5 md:p-6 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-xl hover:shadow-emerald-500/10">
          <div className="absolute -top-4 -right-4 p-4 opacity-5 group-hover:opacity-10 transition-opacity pointer-events-none">
            <Activity className="w-28 h-28 text-emerald-500" />
          </div>
          <div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-3 text-emerald-400 group-hover:scale-110 transition-transform">
              <Activity className="w-5 h-5" />
            </div>
            <h3 className="text-lg md:text-xl font-black text-white mb-1 tracking-tight">Player Analytics Lab</h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-2">Dissect granular ledger stats, auction profile valuations, and career trajectory charts.</p>
          </div>
          <span className="text-emerald-400 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 group-hover:gap-2.5 transition-all mt-auto">
            Access Lab <ArrowRight className="w-4 h-4"/>
          </span>
        </Link>

        {/* QUADRANT 4: INTELLIGENCE WIRE (AMBER) */}
        <Link href="/news" className="group bg-slate-900/60 border border-slate-800 hover:border-amber-500/80 rounded-2xl p-5 md:p-6 transition-all duration-300 relative overflow-hidden flex flex-col justify-between shadow-xl hover:shadow-amber-500/10">
          <div className="absolute -top-4 -right-4 p-4 opacity-5 group-hover:opacity-10 transition-opacity pointer-events-none">
            <Radio className="w-28 h-28 text-amber-500" />
          </div>
          <div>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-3 text-amber-400 group-hover:scale-110 transition-transform">
              <Radio className="w-5 h-5" />
            </div>
            <h3 className="text-lg md:text-xl font-black text-white mb-1 tracking-tight">Intelligence Wire</h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-2">Intercept syndicated live Google RSS feeds for regional scouts, injuries, and global chatter.</p>
          </div>
          <span className="text-amber-400 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 group-hover:gap-2.5 transition-all mt-auto">
            Tap Wire <ArrowRight className="w-4 h-4"/>
          </span>
        </Link>

      </div>
    </div>
  );
}