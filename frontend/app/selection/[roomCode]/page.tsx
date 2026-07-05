"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Users, Trophy, Wallet, Activity, Star } from "lucide-react";

interface Player {
  player_id: string;
  name: string;
  role: string;
  sold_price: number;
}

interface TeamData {
  participant_id: string;
  username: string;
  purse_remaining: number;
  total_spent: number;
  total_players: number;
  analytics: {
    role_distribution: Record<string, number>;
    top_buys: Player[];
  };
  roster: Player[];
}

export default function SelectionAnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const lobbyId = params.roomCode as string;
  
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/team/${lobbyId}?t=${Date.now()}`);
        if (res.ok) {
          const data = await res.json();
          setTeams(data.teams);
        }
      } catch (error) {
        console.error("Failed to fetch teams:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchTeams();
  }, [lobbyId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
        <Activity className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <div className="max-w-7xl mx-auto">
        
        <header className="mb-12 text-center">
          <h1 className="text-4xl font-black text-white uppercase tracking-widest flex items-center justify-center gap-3">
            <Trophy className="text-yellow-500" /> 
            Auction Analysis 
            <Trophy className="text-yellow-500" />
          </h1>
          <p className="text-slate-400 mt-2">Final Squad Breakdowns & Purse Efficiency</p>
        </header>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {teams.map((team) => (
            <div key={team.participant_id} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              
              {/* HEADER */}
              <div className="bg-slate-800/50 p-6 border-b border-slate-700 flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-black text-white">{team.username}&apos;s Squad</h2>
                  <p className="text-slate-400 text-sm">{team.total_players} Players Drafted</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Purse Remaining</p>
                  <p className="text-2xl font-black text-emerald-400">₹{team.purse_remaining}L</p>
                </div>
              </div>

              <div className="p-6 space-y-8">
                
                {/* TOOL 1: PURSE EFFICIENCY BAR */}
                <div>
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Wallet className="w-4 h-4" /> Purse Utilization
                  </h3>
                  <div className="h-4 bg-slate-800 rounded-full overflow-hidden flex">
                    <div 
                      className="bg-emerald-500 h-full" 
                      style={{ width: `${(team.total_spent / (team.total_spent + team.purse_remaining)) * 100}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs mt-2 text-slate-400">
                    <span>Spent: ₹{team.total_spent}L</span>
                    <span>Total Budget: ₹{team.total_spent + team.purse_remaining}L</span>
                  </div>
                </div>

                {/* TOOL 2: SQUAD COMPOSITION (ROLE DISTRIBUTION) */}
                <div>
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Users className="w-4 h-4" /> Squad Balance
                  </h3>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    {Object.entries(team.analytics.role_distribution).map(([role, count]) => (
                      <div key={role} className="bg-slate-800 rounded-lg p-2">
                        <p className="text-xl font-black text-white">{count}</p>
                        <p className="text-[9px] uppercase text-slate-400 tracking-wider truncate">{role}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* TOOL 3: PREMIUM PICKS */}
                <div>
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Star className="w-4 h-4 text-yellow-500" /> Top Premium Buys
                  </h3>
                  <div className="space-y-2">
                    {team.analytics.top_buys.map((player, idx) => (
                      <div key={player.player_id} className="flex justify-between items-center bg-slate-800/30 p-3 rounded-lg border border-slate-700/50">
                        <div className="flex items-center gap-3">
                          <span className="text-slate-500 font-bold">#{idx + 1}</span>
                          <div>
                            <p className="font-bold text-white">{player.name}</p>
                            <p className="text-xs text-slate-400">{player.role}</p>
                          </div>
                        </div>
                        <span className="font-black text-emerald-400">₹{player.sold_price}L</span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}