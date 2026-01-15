export function Leaderboard() {
  // Mock Data for now - will fetch from DB later
  const data = [
    { rank: 1, model: "nvidia/llama-3.1-nemotron-70b", rating: 2850, rd: 30, winRate: "78%" },
    { rank: 2, model: "meta-llama/llama-3.1-405b", rating: 2790, rd: 35, winRate: "72%" },
    { rank: 3, model: "google/gemma-2-27b", rating: 2650, rd: 40, winRate: "65%" },
    { rank: 4, model: "meta-llama/llama-3.1-8b", rating: 2400, rd: 45, winRate: "55%" },
    { rank: 5, model: "Stockfish (Level 1)", rating: 1300, rd: 20, winRate: "10%" },
  ];

  const rows = data.map(row => `
    <tr>
      <td><span class="rank-badge rank-${row.rank}">${row.rank}</span></td>
      <td style="font-weight: 600;">${row.model}</td>
      <td>${row.rating}</td>
      <td>±${row.rd}</td>
      <td>${row.winRate}</td>
    </tr>
  `).join('');

  return `
    <div class="card animate-fade-in">
      <div class="flex justify-between items-center">
        <h2>🏆 Leaderboard</h2>
        <span style="font-size: 0.9rem; color: var(--text-secondary);">Last Updated: Q4 2025</span>
      </div>
      <table class="leaderboard-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Model Agent</th>
            <th>Elo Rating</th>
            <th>Deviation (RD)</th>
            <th>Win Rate</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    </div>
  `;
}
