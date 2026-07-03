"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Swords, Plus, LogIn, Activity } from "lucide-react";

export default function AuctionLandingPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateRoom = async () => {
    if (!username.trim()) {
      setError("Please enter a nickname first.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/lobby/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create lobby");

      // Save tokens in browser memory for persistent refresh protection
      sessionStorage.setItem("crick_lobby_id", data.lobby_id);
      sessionStorage.setItem("crick_participant_id", data.participant_id);
      sessionStorage.setItem("crick_username", data.username);

      // Instantly route them into the live arena
      router.push(`/auction/${data.room_code}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleJoinRoom = async () => {
    if (!username.trim() || !roomCode.trim()) {
      setError("Both Nickname and Room Code are required.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/lobby/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_code: roomCode.trim().toUpperCase(),
          username: username.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to join lobby");

      sessionStorage.setItem("crick_lobby_id", data.lobby_id);
      sessionStorage.setItem("crick_participant_id", data.participant_id);
      sessionStorage.setItem("crick_username", data.username);

      router.push(`/auction/${data.room_code}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900/60 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md">
        
        <div className="text-center mb-8">
          <div className="inline-flex p-3 bg-blue-500/10 rounded-xl text-blue-500 mb-3">
            <Swords className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white">Party Auction Room</h1>
          <p className="text-xs text-slate-400 mt-1">No registration needed. Create or join a lobby instantly.</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/40 border border-red-900/50 text-red-300 rounded-xl text-xs">
            {error}
          </div>
        )}

        <div className="space-y-4 text-xs">
          <div>
            <label className="text-slate-400 block mb-1 font-bold uppercase tracking-wider">Your Nickname</label>
            <input
              type="text"
              maxLength={12}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g., Arun"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white text-sm outline-none focus:border-blue-500 transition-all font-medium"
            />
          </div>

          <div className="pt-4 border-t border-slate-800/80 grid grid-cols-1 gap-3">
            <button
              onClick={handleCreateRoom}
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-black uppercase py-3 rounded-xl transition-all shadow-md flex items-center justify-center gap-2 text-xs tracking-wider"
            >
              {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              <span>Create New Lobby</span>
            </button>

            <div className="relative flex py-2 items-center text-slate-600">
              <div className="flex-grow border-t border-slate-800"></div>
              <span className="flex-shrink mx-3 uppercase text-[10px] font-black tracking-widest">Or Join Existing</span>
              <div className="flex-grow border-t border-slate-800"></div>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="ROOM CODE (e.g. CRK-XYZ)"
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-white text-sm outline-none focus:border-emerald-500 transition-all uppercase w-2/3 tracking-widest font-mono text-center"
              />
              <button
                onClick={handleJoinRoom}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-black uppercase rounded-xl transition-all flex items-center justify-center gap-1 w-1/3 text-[11px] tracking-wider"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Enter</span>
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}