"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Trophy } from "lucide-react";

export default function SelectionEntryPage() {
  const [roomCode, setRoomCode] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (roomCode.trim()) {
      router.push(`/selection/${roomCode.trim()}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center">
        <Trophy className="w-16 h-16 text-yellow-500 mx-auto mb-6" />
        <h1 className="text-3xl font-black text-white uppercase tracking-widest mb-2">
          Post-Auction
        </h1>
        <p className="text-slate-400 mb-8">Enter a Room Code to view the final squads and analytics.</p>
        
        <form onSubmit={handleSearch} className="space-y-4">
          <input
            type="text"
            placeholder="Enter Room Code (e.g., CRK-VSI4)"
            value={roomCode}
            onChange={(e) => setRoomCode(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-center uppercase tracking-widest"
            required
          />
          <button
            type="submit"
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 uppercase tracking-wider"
          >
            <Search className="w-5 h-5" />
            Analyze Lobby
          </button>
        </form>
      </div>
    </div>
  );
}