# voice_input.py - 음성인식 컴포넌트
import streamlit as st
import streamlit.components.v1 as components
import uuid

def voice_input_component(key=None):
    """음성 입력 컴포넌트"""
    
    if key is None:
        key = str(uuid.uuid4())
    
    # HTML/JavaScript 컴포넌트
    voice_html = f"""
    <div id="voice-container-{key}">
        <style>
            .voice-button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 50px;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }}
            
            .voice-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
            }}
            
            .voice-button.recording {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                animation: pulse 1.5s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4); }}
                50% {{ box-shadow: 0 4px 25px rgba(245, 87, 108, 0.6); }}
                100% {{ box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4); }}
            }}
            
            .voice-result {{
                margin-top: 15px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
                min-height: 60px;
                border: 2px solid #e9ecef;
                font-size: 16px;
                line-height: 1.5;
            }}
            
            .voice-status {{
                color: #666;
                font-size: 14px;
                margin-top: 10px;
                font-style: italic;
            }}
        </style>
        
        <button id="voiceBtn-{key}" class="voice-button" onclick="toggleRecording_{key}()">
            <span id="micIcon-{key}">🎤</span>
            <span id="btnText-{key}">말로 입력하기</span>
        </button>
        
        <div id="result-{key}" class="voice-result"></div>
        <div id="status-{key}" class="voice-status"></div>
        
        <script>
            let recognition_{key} = null;
            let isRecording_{key} = false;
            
            // 음성인식 초기화
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition_{key} = new SpeechRecognition();
                recognition_{key}.lang = 'ko-KR';
                recognition_{key}.continuous = true;
                recognition_{key}.interimResults = true;
                
                recognition_{key}.onstart = function() {{
                    document.getElementById('status-{key}').textContent = '🔴 듣고 있습니다... 말씀해 주세요';
                    document.getElementById('voiceBtn-{key}').classList.add('recording');
                    document.getElementById('micIcon-{key}').textContent = '⏹️';
                    document.getElementById('btnText-{key}').textContent = '중지하기';
                }};
                
                recognition_{key}.onresult = function(event) {{
                    let finalTranscript = '';
                    let interimTranscript = '';
                    
                    for (let i = event.resultIndex; i < event.results.length; i++) {{
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {{
                            finalTranscript += transcript + ' ';
                        }} else {{
                            interimTranscript += transcript;
                        }}
                    }}
                    
                    const resultDiv = document.getElementById('result-{key}');
                    resultDiv.innerHTML = '<strong>인식된 내용:</strong><br>' + 
                                         (finalTranscript || interimTranscript);
                    
                    // Streamlit에 데이터 전송
                    if (finalTranscript) {{
                        const textarea = window.parent.document.querySelector('textarea');
                        if (textarea) {{
                            textarea.value = finalTranscript.trim();
                            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                }};
                
                recognition_{key}.onerror = function(event) {{
                    console.error('Speech recognition error:', event.error);
                    document.getElementById('status-{key}').textContent = '❌ 오류: ' + event.error;
                    if (event.error === 'not-allowed') {{
                        document.getElementById('status-{key}').textContent = 
                            '❌ 마이크 권한이 필요합니다. 브라우저 설정에서 마이크를 허용해주세요.';
                    }}
                    resetButton_{key}();
                }};
                
                recognition_{key}.onend = function() {{
                    document.getElementById('status-{key}').textContent = '✅ 음성 입력 완료';
                    resetButton_{key}();
                }};
            }} else {{
                document.getElementById('voiceBtn-{key}').disabled = true;
                document.getElementById('status-{key}').textContent = 
                    '⚠️ 이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 브라우저를 사용해주세요.';
            }}
            
            function toggleRecording_{key}() {{
                if (!recognition_{key}) return;
                
                if (isRecording_{key}) {{
                    recognition_{key}.stop();
                    isRecording_{key} = false;
                }} else {{
                    document.getElementById('result-{key}').innerHTML = '';
                    recognition_{key}.start();
                    isRecording_{key} = true;
                }}
            }}
            
            function resetButton_{key}() {{
                document.getElementById('voiceBtn-{key}').classList.remove('recording');
                document.getElementById('micIcon-{key}').textContent = '🎤';
                document.getElementById('btnText-{key}').textContent = '말로 입력하기';
                isRecording_{key} = false;
            }}
        </script>
    </div>
    """
    
    components.html(voice_html, height=200)

def get_voice_input():
    """간단한 음성 입력 버튼"""
    
    html_code = """
    <div>
        <button onclick="startVoice()" style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 50px;
            cursor: pointer;
            margin: 10px 0;
        ">
            🎤 음성으로 입력
        </button>
        <div id="voiceResult" style="margin-top: 10px; color: #666;"></div>
    </div>
    
    <script>
    function startVoice() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            recognition.lang = 'ko-KR';
            recognition.continuous = false;
            recognition.interimResults = true;
            
            recognition.onstart = function() {
                document.getElementById('voiceResult').textContent = '🔴 듣고 있습니다...';
            };
            
            recognition.onresult = function(event) {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                // 부모 프레임의 textarea에 텍스트 입력
                const textareas = window.parent.document.querySelectorAll('textarea');
                if (textareas.length > 0) {
                    textareas[0].value = text;
                    textareas[0].dispatchEvent(new Event('input', { bubbles: true }));
                    document.getElementById('voiceResult').textContent = '✅ 입력 완료: ' + text;
                }
            };
            
            recognition.onerror = function(event) {
                document.getElementById('voiceResult').textContent = '❌ 오류: ' + event.error;
            };
            
            recognition.start();
        } else {
            alert('음성 인식이 지원되지 않는 브라우저입니다. Chrome을 사용해주세요.');
        }
    }
    </script>
    """
    
    components.html(html_code, height=100)
