# services/voice_recorder.py
import streamlit as st
import streamlit.components.v1 as components
import base64
import json

def create_voice_recorder():
    """
    브라우저 네이티브 녹음 기능을 사용하는 커스텀 음성 녹음 컴포넌트
    클릭 한 번으로 바로 녹음 시작
    """
    
    recorder_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .recorder-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 20px;
            }
            
            .record-button {
                width: 200px;
                height: 60px;
                border: none;
                border-radius: 30px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            
            .record-button.idle {
                background: linear-gradient(135deg, #4CAF50, #45a049);
                color: white;
            }
            
            .record-button.idle:hover {
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
            }
            
            .record-button.recording {
                background: linear-gradient(135deg, #f44336, #da190b);
                color: white;
                animation: pulse 1.5s infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .status {
                font-size: 14px;
                color: #666;
                text-align: center;
            }
            
            .audio-preview {
                margin-top: 20px;
                display: none;
            }
            
            .dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #f44336;
                margin-right: 5px;
                animation: blink 1s infinite;
            }
            
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }
        </style>
    </head>
    <body>
        <div class="recorder-container">
            <button id="recordBtn" class="record-button idle" onclick="handleRecord()">
                <span id="btnIcon">🎤</span>
                <span id="btnText">녹음 시작</span>
            </button>
            
            <div id="status" class="status">준비됨</div>
            
            <audio id="audioPreview" class="audio-preview" controls></audio>
        </div>
        
        <script>
            let mediaRecorder = null;
            let audioChunks = [];
            let isRecording = false;
            let stream = null;
            
            async function handleRecord() {
                const btn = document.getElementById('recordBtn');
                const btnIcon = document.getElementById('btnIcon');
                const btnText = document.getElementById('btnText');
                const status = document.getElementById('status');
                const audioPreview = document.getElementById('audioPreview');
                
                if (!isRecording) {
                    // 녹음 시작
                    try {
                        // 마이크 권한 요청 및 스트림 가져오기
                        stream = await navigator.mediaDevices.getUserMedia({ 
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                sampleRate: 44100
                            } 
                        });
                        
                        // MediaRecorder 생성
                        mediaRecorder = new MediaRecorder(stream, {
                            mimeType: 'audio/webm'
                        });
                        
                        audioChunks = [];
                        
                        // 데이터 수집
                        mediaRecorder.ondataavailable = (event) => {
                            if (event.data.size > 0) {
                                audioChunks.push(event.data);
                            }
                        };
                        
                        // 녹음 완료 처리
                        mediaRecorder.onstop = async () => {
                            // Blob 생성
                            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                            
                            // 미리듣기
                            const audioUrl = URL.createObjectURL(audioBlob);
                            audioPreview.src = audioUrl;
                            audioPreview.style.display = 'block';
                            
                            // Base64로 변환하여 Streamlit에 전송
                            const reader = new FileReader();
                            reader.onloadend = () => {
                                const base64Audio = reader.result.split(',')[1];
                                
                                // Streamlit으로 데이터 전송
                                window.parent.postMessage({
                                    type: 'streamlit:setComponentValue',
                                    data: {
                                        audio_data: base64Audio,
                                        mime_type: 'audio/webm'
                                    }
                                }, '*');
                            };
                            reader.readAsDataURL(audioBlob);
                            
                            // 상태 업데이트
                            status.innerHTML = '✅ 녹음 완료! 자동으로 텍스트 변환 중...';
                        };
                        
                        // 녹음 시작
                        mediaRecorder.start();
                        isRecording = true;
                        
                        // UI 업데이트
                        btn.className = 'record-button recording';
                        btnIcon.textContent = '⏹️';
                        btnText.textContent = '녹음 중지';
                        status.innerHTML = '<span class="dot"></span>녹음 중... 말씀해 주세요';
                        audioPreview.style.display = 'none';
                        
                    } catch (err) {
                        console.error('마이크 접근 오류:', err);
                        status.innerHTML = '❌ 마이크 접근 실패. 권한을 확인하세요.';
                    }
                    
                } else {
                    // 녹음 중지
                    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                        mediaRecorder.stop();
                        
                        // 스트림 정지
                        if (stream) {
                            stream.getTracks().forEach(track => track.stop());
                        }
                        
                        isRecording = false;
                        
                        // UI 업데이트
                        btn.className = 'record-button idle';
                        btnIcon.textContent = '🎤';
                        btnText.textContent = '녹음 시작';
                        status.innerHTML = '처리 중...';
                    }
                }
            }
            
            // 페이지 로드시 자동으로 권한 체크
            window.onload = async () => {
                try {
                    const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
                    if (permissionStatus.state === 'granted') {
                        document.getElementById('status').innerHTML = '✅ 마이크 준비됨';
                    }
                } catch (err) {
                    // 권한 API를 지원하지 않는 브라우저
                }
            };
        </script>
    </body>
    </html>
    """
    
    # 컴포넌트 렌더링
    component_value = components.html(
        recorder_html,
        height=200,
        scrolling=False
    )
    
    return component_value

def get_audio_recorder_component():
    """
    Streamlit 페이지에서 사용할 음성 녹음 컴포넌트
    """
    st.markdown("### 🎤 음성으로 입력하기")
    
    # 커스텀 컴포넌트 사용
    audio_data = create_voice_recorder()
    
    # 녹음 데이터 처리
    if audio_data:
        return audio_data.get('audio_data'), audio_data.get('mime_type')
    
    return None, None
