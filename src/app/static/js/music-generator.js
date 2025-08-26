/**
 * 音楽生成機能のメインモジュール
 */
function musicGenerator() {
    return {
        // 初期化フラグ
        isLoading: true,

        // タグデータ（初期化時にAPIから取得）
        tagData: {},
        genres: [],
        moods: [],
        scenes: [],
        instruments: [],
        tempos: [],
        eras: [],
        regions: [],

        // 選択状態
        selectedTags: {
            genre: [],
            mood: [],
            scene: [],
            instrument: [],
            tempo: [],
            era: [],
            region: []
        },

        // 生成設定
        duration: 10,

        // 状態管理
        isGenerating: false,
        generatedMusic: false,
        progress: 0,
        generatingMessage: 'プロンプトを生成中...',

        // 結果データ
        generatedPrompt: '',
        audioUrl: '',
        downloadUrl: '',
        generationTime: 0,
        fileSize: '0 MB',

        // メソッド
        toggleTag(category, tag) {
            if (!this.selectedTags[category]) {
                this.selectedTags[category] = [];
            }
            const index = this.selectedTags[category].indexOf(tag);
            if (index > -1) {
                this.selectedTags[category].splice(index, 1);
            } else {
                // カテゴリごとの最大選択数を制限
                const maxSelections = {
                    genre: 1,       // ジャンルは排他的（1つのみ）
                    mood: 1,        // ムードも排他的
                    scene: 2,       // シーンは2つまで
                    instrument: 5,  // 楽器は5つまで
                    tempo: 1,       // テンポは排他的
                    era: 1,         // 時代は排他的
                    region: 1       // 地域は排他的
                };
                const maxCount = maxSelections[category] || 3;
                if (this.selectedTags[category].length < maxCount) {
                    this.selectedTags[category].push(tag);
                }
            }
        },

        canGenerate() {
            return Object.values(this.selectedTags).some(tags => tags.length > 0);
        },

        async generateMusic() {
            this.isGenerating = true;
            this.progress = 0;

            // プログレスシミュレーション
            const progressInterval = setInterval(() => {
                if (this.progress < 90) {
                    this.progress += Math.random() * 15;

                    if (this.progress > 30) {
                        this.generatingMessage = '音楽を生成中...';
                    }
                    if (this.progress > 60) {
                        this.generatingMessage = 'マスタリング中...';
                    }
                }
            }, 500);

            try {
                // APIリクエストデータ準備
                const requestData = {
                    genre_tags: this.selectedTags.genre || [],
                    mood_tags: this.selectedTags.mood || [],
                    scene_tags: this.selectedTags.scene || [],
                    instrument_tags: this.selectedTags.instrument || [],
                    tempo_tags: this.selectedTags.tempo || [],
                    era_tags: this.selectedTags.era || [],
                    region_tags: this.selectedTags.region || [],
                    duration_seconds: this.duration
                };

                // API呼び出し
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });

                const data = await response.json();

                clearInterval(progressInterval);
                this.progress = 100;
                this.isGenerating = false;

                if (data.success) {
                    this.generatedMusic = true;
                    this.generatedPrompt = data.prompt;

                    // Base64音声データがある場合はオーディオURLを作成
                    if (data.audio_data) {
                        console.log('Audio data length:', data.audio_data.length);

                        // データURLとして直接設定する方法も試す
                        this.audioUrl = 'data:audio/mpeg;base64,' + data.audio_data;
                        console.log('Audio URL created as data URL');

                        // Blobも作成（ダウンロード用）
                        const audioBlob = this.base64ToBlob(data.audio_data, 'audio/mpeg');
                        console.log('Blob size:', audioBlob.size);
                        this.downloadUrl = URL.createObjectURL(audioBlob);
                    } else {
                        console.log('No audio data in response');
                    }

                    this.generationTime = data.generation_time ? data.generation_time.toFixed(1) : '0';
                    this.fileSize = data.file_size_bytes ?
                        `${(data.file_size_bytes / 1024 / 1024).toFixed(1)} MB` : '0 MB';
                } else {
                    alert(`生成エラー: ${data.error_message || '不明なエラー'}`);
                }
            } catch (error) {
                clearInterval(progressInterval);
                this.isGenerating = false;
                console.error('生成エラー:', error);
                alert('音楽生成中にエラーが発生しました');
            }
        },

        base64ToBlob(base64, mimeType) {
            const byteCharacters = atob(base64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            return new Blob([byteArray], { type: mimeType });
        },

        resetGenerator() {
            this.generatedMusic = false;
            this.selectedTags = {
                genre: [],
                mood: [],
                scene: [],
                instrument: [],
                tempo: [],
                era: [],
                region: []
            };
            this.generatedPrompt = '';
            if (this.audioUrl && this.audioUrl.startsWith('blob:')) {
                URL.revokeObjectURL(this.audioUrl);
            }
            if (this.downloadUrl && this.downloadUrl.startsWith('blob:')) {
                URL.revokeObjectURL(this.downloadUrl);
            }
            this.audioUrl = '';
            this.downloadUrl = '';
        },

        // 初期化処理
        async init() {
            try {
                const response = await fetch('/api/tags');
                const data = await response.json();
                console.log('Received tag data:', data);
                this.tagData = data;

                // カテゴリごとにタグを整理（オブジェクト全体を保持）
                if (data.genre && data.genre.tags) {
                    this.genres = data.genre.tags;
                    console.log('Genres:', this.genres);
                }
                if (data.mood && data.mood.tags) {
                    this.moods = data.mood.tags;
                    console.log('Moods:', this.moods);
                }
                if (data.scene && data.scene.tags) {
                    this.scenes = data.scene.tags;
                    console.log('Scenes:', this.scenes);
                }
                if (data.instrument && data.instrument.tags) {
                    this.instruments = data.instrument.tags;
                }
                if (data.tempo && data.tempo.tags) {
                    this.tempos = data.tempo.tags;
                }
                if (data.era && data.era.tags) {
                    this.eras = data.era.tags;
                }
                if (data.region && data.region.tags) {
                    this.regions = data.region.tags;
                }

                this.isLoading = false;
            } catch (error) {
                console.error('タグデータの取得に失敗:', error);
                // フォールバックデータ
                this.genres = ['RPG', 'アクション', 'パズル', 'ホラー', 'アドベンチャー'];
                this.moods = ['エピック', 'ミステリアス', 'エネルギッシュ', 'リラックス', 'ダーク'];
                this.scenes = ['戦闘', 'タイトル', 'ボス戦', '探索', 'エンディング'];
                this.isLoading = false;
            }
        }
    }
}