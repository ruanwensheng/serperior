import React, { useState } from 'react';

const ChatInterface = ({ field, startDate, endDate, keywords = [] }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Update greeting when context changes
    React.useEffect(() => {
        const greeting = `Xin chào! Bạn muốn hỏi gì về mục ${field || '...'} trong khoảng thời gian ${endDate || '...'} tới ${startDate || '...'}?`;
        setMessages([{ role: 'assistant', content: greeting }]);
    }, [field, startDate, endDate]);

    const sendMessage = async (text) => {
        const msgToSend = text || input;
        if (!msgToSend.trim()) return;

        const userMsg = { role: 'user', content: msgToSend };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msgToSend })
            });

            const data = await response.json();

            if (data.success) {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: data.response,
                    sources: data.sources
                }]);
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: 'Lỗi: ' + (data.error || 'Server error') }]);
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Lỗi kết nối: ' + error.message }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container flex flex-col h-full">
            <div className="messages flex-1 overflow-y-auto mb-4 space-y-4">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`p-3 rounded-lg max-w-[80%] ${msg.role === 'user' ? 'bg-blue-600 text-white self-end ml-auto' : 'bg-white text-gray-800 self-start mr-auto border'}`}>
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        {msg.sources && msg.sources.length > 0 && (
                            <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                                <strong>Nguồn:</strong>
                                <ul className="list-disc pl-4 mt-1">
                                    {msg.sources.map((src, i) => (
                                        <li key={i}>{src}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                ))}
                {isLoading && <div className="text-gray-500 italic">Đang suy nghĩ...</div>}
            </div>

            {/* Suggested Keywords */}
            {keywords.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                    {keywords.slice(0, 5).map((kw, idx) => (
                        <button
                            key={idx}
                            onClick={() => sendMessage(kw.text || kw.entity)} // Handle both entity formats
                            className="text-xs bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full hover:bg-emerald-200 transition-colors"
                        >
                            {kw.text || kw.entity}
                        </button>
                    ))}
                </div>
            )}

            <div className="input-area flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage(input)}
                    placeholder="Hỏi về tin tức..."
                    className="flex-1 p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                    onClick={() => sendMessage(input)}
                    disabled={isLoading}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
                >
                    Gửi
                </button>
            </div>
        </div>
    );
};

export default ChatInterface;
