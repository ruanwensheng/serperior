import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import ChatInterface from './ChatInterface';

const API_BASE_URL = 'http://127.0.0.1:8000';

const FIELDS = [
  { value: 'kinh-doanh', label: 'Kinh doanh' },
  { value: 'thoi-su', label: 'Thời sự' },
  { value: 'phap-luat', label: 'Pháp luật' },
  { value: 'du-lich', label: 'Du lịch' },
  { value: 'bat-dong-san', label: 'Bất động sản' }
];

const Dashboard = () => {
  const [selectedField, setSelectedField] = useState('kinh-doanh');
  const [startDate, setStartDate] = useState('2024-12-20');
  const [endDate, setEndDate] = useState('2024-12-18');
  const [numArticles, setNumArticles] = useState(5);
  const [articles, setArticles] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCrawl = async () => {
    setLoading(true);
    setError(null);
    setArticles([]);
    setEntities([]);

    try {
      // Use the optimized endpoint with reset_db=true (Clear DB each time)
      // Also using 127.0.0.1 to avoid localhost IPv6 issues
      const response = await fetch(
        `${API_BASE_URL}/api/v1/analyze/full?start_date=${startDate}&end_date=${endDate}&field=${selectedField}&num_articles=${numArticles}&reset_db=true`
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Fetch failed:', response.status, errorText);
        throw new Error(`Failed to fetch data: ${response.status} ${errorText}`);
      }

      const data = await response.json();

      if (data.success && data.data) {
        setArticles(data.data.articles || []);

        // Auto-populate analysis results (Entities/Keywords)
        const entityData = data.data.entity?.entities || [];
        setEntities(entityData);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    if (articles.length === 0) {
      setError('No articles to export');
      return;
    }

    try {
      const csvContent = convertToCSV(articles);
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      link.setAttribute('href', url);
      link.setAttribute('download', `dantri_export_${timestamp}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      setError('Failed to export CSV');
    }
  };

  const convertToCSV = (data) => {
    if (data.length === 0) return '';
    const headers = ['date', 'title', 'body', 'url'];
    const csvRows = [headers.join(',')];
    for (const row of data) {
      const values = headers.map(header => {
        const value = row[header] || '';
        const escaped = String(value).replace(/"/g, '""');
        return `"${escaped}"`;
      });
      csvRows.push(values.join(','));
    }
    return '\uFEFF' + csvRows.join('\n');
  };

  const getWordCloudStyle = (index, total) => {
    const sizes = ['text-5xl', 'text-4xl', 'text-3xl', 'text-2xl', 'text-xl', 'text-lg', 'text-base'];
    const colors = ['text-emerald-600', 'text-emerald-500', 'text-green-600', 'text-green-500', 'text-teal-600', 'text-teal-500', 'text-emerald-400'];
    const sizeIndex = Math.min(index, sizes.length - 1);
    const colorIndex = index % colors.length;
    return `${sizes[sizeIndex]} ${colors[colorIndex]} font-bold`;
  };

  const entityBarData = entities.slice(0, 10).map(e => ({
    name: e.text || e.entity,
    count: e.count
  }));

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-green-50">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        * { font-family: 'Inter', sans-serif; }
      `}</style>

      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-64 bg-white border-r border-gray-200 shadow-sm flex flex-col shrink-0">
          <div className="p-6">
            <img src="/ok.png" alt="Serperior" className="w-40 h-auto mb-2" />
            <p className="text-sm text-gray-500">News Crawler Dashboard</p>
          </div>

          <nav className="px-4 space-y-1 flex-1">
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-2">
              Lĩnh vực
            </div>
            {FIELDS.map(field => (
              <button
                key={field.value}
                onClick={() => setSelectedField(field.value)}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${selectedField === field.value
                  ? 'bg-emerald-50 text-emerald-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
                  }`}
              >
                {field.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content (Window Scroll) */}
        <div className="flex-1 overflow-auto flex flex-col">
          {/* Top Bar (Controls) */}
          <div className="bg-white border-b border-gray-200 shadow-sm shrink-0 sticky top-0 z-10">
            <div className="px-8 py-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-800">
                  {FIELDS.find(f => f.value === selectedField)?.label}
                </h2>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Từ ngày</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Đến ngày</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Số bài</label>
                    <input
                      type="number"
                      value={numArticles}
                      onChange={(e) => setNumArticles(parseInt(e.target.value))}
                      min="1"
                      max="20"
                      className="w-16 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>

                  <button
                    onClick={handleCrawl}
                    disabled={loading}
                    className="px-6 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm"
                  >
                    {loading ? 'Đang xử lý...' : 'Fetch & Analyze'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-8 pb-0">
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            </div>
          )}

          {/* Main Content Area (Grid) */}
          {articles.length > 0 && (
            <div className="p-8 grid grid-cols-12 gap-6 items-start">

              {/* Left Column: Analysis & Articles (Grow naturally) */}
              <div className="col-span-8 flex flex-col gap-6">

                {/* Entity Analysis (Visuals) */}
                {entities.length > 0 && (
                  <div className="grid grid-cols-2 gap-6 shrink-0">
                    {/* Word Cloud */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                      <div className="px-6 py-4 border-b border-gray-200">
                        <h3 className="text-lg font-semibold text-gray-800">Thực thể nổi bật</h3>
                      </div>
                      <div className="p-6 bg-gradient-to-br from-emerald-50 to-green-50">
                        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-3 min-h-[200px]">
                          {entities.slice(0, 15).map((entity, idx) => (
                            <span
                              key={idx}
                              className={`${getWordCloudStyle(idx, entities.length)} hover:scale-110 transition-transform cursor-default`}
                              style={{ opacity: 1 - (idx * 0.03) }}
                            >
                              {entity.text || entity.entity}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Bar Chart */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                      <div className="px-6 py-4 border-b border-gray-200">
                        <h3 className="text-lg font-semibold text-gray-800">Top 5 thực thể</h3>
                      </div>
                      <div className="p-4">
                        <ResponsiveContainer width="100%" height={200}>
                          <BarChart data={entityBarData.slice(0, 5)} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                            <XAxis type="number" hide />
                            <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 12 }} />
                            <Tooltip />
                            <Bar dataKey="count" fill="#10b981" radius={[0, 4, 4, 0]} barSize={20} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                )}

                {/* Article List */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex-1">
                  <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">Danh sách bài báo</h3>
                      <p className="text-sm text-gray-500 mt-0.5">{articles.length} bài báo</p>
                    </div>
                    <button
                      onClick={handleExportCSV}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
                    >
                      Export CSV
                    </button>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {articles.map((article, idx) => (
                      <div key={idx} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-start gap-4">
                          <div className="flex-shrink-0 w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                            <span className="text-emerald-700 font-bold">{idx + 1}</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-gray-900 mb-1 line-clamp-1">{article.title}</h4>
                            <p className="text-sm text-gray-500 line-clamp-2">{article.body}</p>
                            <div className="flex items-center gap-4 mt-2">
                              <span className="text-xs text-gray-400">{article.date}</span>
                              <a href={article.url} target="_blank" rel="noopener noreferrer" className="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
                                Xem bài viết
                              </a>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Column: Chatbot (Sticky) */}
              <div className="col-span-4 sticky top-24">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col h-[700px]">
                  <div className="px-6 py-4 border-b border-gray-200 bg-emerald-50">
                    <h3 className="text-lg font-semibold text-gray-800">AI Assistant</h3>
                    <p className="text-xs text-emerald-600">Hỏi đáp về dữ liệu vừa thu thập</p>
                  </div>
                  <div className="flex-1 overflow-hidden p-0">
                    <ChatInterface
                      field={FIELDS.find(f => f.value === selectedField)?.label}
                      startDate={startDate}
                      endDate={endDate}
                      keywords={entities}
                    />
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* Empty State */}
          {!loading && articles.length === 0 && (
            <div className="flex-1 flex items-center justify-center p-12">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center max-w-md">
                <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">📰</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">
                  Chưa có dữ liệu
                </h3>
                <p className="text-gray-500 mb-6">
                  Chọn lĩnh vực, khoảng thời gian và nhấn "Fetch & Analyze" để bắt đầu
                </p>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default Dashboard;