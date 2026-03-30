import { CryptoStatsCard } from "@/components/ui/stats-card-2"; // Adjust the import path

const CryptoStatsCardDemo = () => {
  // Mock data mimicking the structure from the image
  const marketCapData = {
    usd: 4000000000000, // 4T
    change: 7.79,
  };

  const sparklineChartData = [
    50, 52, 48, 55, 60, 58, 62, 70, 68, 75, 72, 80, 78, 85, 82, 70, 65, 72, 78, 88, 92, 90
  ];

  const dominanceData = [
    { name: "Bitcoin", percentage: 59.02, color: "bg-blue-500" },
    { name: "Ethereum", percentage: 13.11, color: "bg-red-500" },
    { name: "Others", percentage: 27.87, color: "bg-cyan-400" },
  ];

  const coinData = [
    {
      iconUrl: "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=100&h=100&fit=crop&q=80",
      name: "Bitcoin",
      symbol: "BTCUSD",
      price: 118624,
      change: -0.04,
    },
    {
      iconUrl: "https://images.unsplash.com/photo-1622736136809-ce0bfebdd198?w=100&h=100&fit=crop&q=80",
      name: "Ethereum",
      symbol: "ETHUSD",
      price: 4349.2,
      change: -0.04,
    },
  ];

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background p-4">
      <CryptoStatsCard
        marketCapUSD={marketCapData.usd}
        marketCapChange={marketCapData.change}
        chartData={sparklineChartData}
        dominanceData={dominanceData}
        coinData={coinData}
      />
    </div>
  );
};

export default CryptoStatsCardDemo;
