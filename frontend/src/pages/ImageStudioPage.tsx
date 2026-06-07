import React, { useState, useEffect, useMemo } from 'react';
import { ArrowLeft, ImageIcon, Download, Loader2 } from 'lucide-react';
import ThemedSelect from '../components/ThemedSelect';
import { useNavigate } from 'react-router-dom';
import type { ImageToolOut, GeneratedImageOut } from '../api';
import { GeneratedImagesService, ImageToolsService } from '../api';

const ASPECT_RATIO_PRESETS = [
  { label: '1:1',  width: 1024, height: 1024 },
  { label: '4:3',  width: 1024, height: 768  },
  { label: '3:4',  width: 768,  height: 1024 },
  { label: '16:9', width: 1024, height: 576  },
  { label: '9:16', width: 576,  height: 1024 },
  { label: '3:2',  width: 1536, height: 1024 },
  { label: '2:3',  width: 1024, height: 1536 },
];

type GenerationMode = 'txt2img' | 'img2img';
type Img2ImgSourceMode = 'upload' | 'history';

const ImageStudioPage: React.FC = () => {
  const navigate = useNavigate();

  const [tools, setTools] = useState<ImageToolOut[]>([]);
  const [loadingInit, setLoadingInit] = useState(true);
  const [mode, setMode] = useState<GenerationMode>('txt2img');

  const [selectedToolId, setSelectedToolId] = useState<number | null>(null);
  const availableTools = useMemo(
    () => (mode === 'img2img' ? tools.filter(t => t.support_img2img) : tools),
    [mode, tools],
  );

  const [positivePrompt, setPositivePrompt] = useState('');
  const [imgWidth, setImgWidth] = useState(1024);
  const [imgHeight, setImgHeight] = useState(1024);
  const [img2imgSourceMode, setImg2imgSourceMode] = useState<Img2ImgSourceMode>('upload');
  const [sourceImage, setSourceImage] = useState<File | null>(null);
  const [generatedImages, setGeneratedImages] = useState<GeneratedImageOut[]>([]);
  const [loadingGeneratedImages, setLoadingGeneratedImages] = useState(false);
  const [selectedHistoryObjectKey, setSelectedHistoryObjectKey] = useState<string | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [revisedPrompt, setRevisedPrompt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      try {
        const toolsData = await ImageToolsService.listImageTools();
        setTools(toolsData);
        if (toolsData.length > 0) {
          setSelectedToolId(toolsData[0].id);
        }
      } catch (e) {
        console.error('初始化失败:', e);
      } finally {
        setLoadingInit(false);
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (mode !== 'img2img' || img2imgSourceMode !== 'history') return;
    const loadGeneratedImages = async () => {
      setLoadingGeneratedImages(true);
      try {
        const page = await GeneratedImagesService.listGeneratedImagesApiV1GeneratedImagesGet(1, 20);
        setGeneratedImages(page.items ?? []);
      } catch (e) {
        console.error('加载历史生成图失败:', e);
        setGeneratedImages([]);
      } finally {
        setLoadingGeneratedImages(false);
      }
    };
    loadGeneratedImages();
  }, [mode, img2imgSourceMode]);

  useEffect(() => {
    if (availableTools.length === 0) {
      setSelectedToolId(null);
      return;
    }
    if (!selectedToolId || !availableTools.some(t => t.id === selectedToolId)) {
      setSelectedToolId(availableTools[0].id);
    }
  }, [availableTools, selectedToolId]);

  const handleGenerate = async () => {
    if (!selectedToolId || !positivePrompt.trim()) return;
    setIsGenerating(true);
    setError(null);
    setResultImage(null);
    setRevisedPrompt(null);
    try {
      const w = imgWidth;
      const h = imgHeight;
      const res = mode === 'img2img'
        ? (
          img2imgSourceMode === 'history'
            ? await ImageToolsService.img2ImgByReference(selectedToolId, {
              prompt: positivePrompt,
              width: w,
              height: h,
              object_key: selectedHistoryObjectKey,
            })
            : await ImageToolsService.img2ImgApiV1ImageToolsToolIdImg2ImgPost(selectedToolId, {
              prompt: positivePrompt,
              width: w,
              height: h,
              image: sourceImage as Blob,
            })
        )
        : await ImageToolsService.generateImage(selectedToolId, {
          prompt: positivePrompt,
          width: w,
          height: h,
        });
      setResultImage(res.image_url);
      setRevisedPrompt(res.revised_prompt ?? null);
    } catch (e: unknown) {
      setError((mode === 'img2img' ? '编辑失败: ' : '生成失败: ') + String(e));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!resultImage) return;
    const a = document.createElement('a');
    a.href = resultImage;
    a.download = `generated_${Date.now()}.png`;
    a.click();
  };

  const inputClass = 'w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl text-gray-800 placeholder-gray-500 outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-sm';
  const selectClass = 'w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl text-gray-800 outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-sm';
  const labelClass = 'block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide';

  if (loadingInit) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={24} className="animate-spin text-gray-500" />
      </div>
    );
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 rounded-xl transition text-sm"
          >
            <ArrowLeft size={15} />
            返回
          </button>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">图像工作台</h2>
            <p className="text-xs text-gray-500 mt-0.5">使用 AI 生成精美图像</p>
          </div>
        </div>

        {tools.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🎨</div>
            <p className="text-gray-600 mb-2">尚未配置文生图模型</p>
            <button onClick={() => navigate('/image-tools')}
              className="mt-4 px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition-all text-sm">
              前往配置
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Config */}
            <div className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 space-y-5">
              {/* Tool selector */}
              <div>
                <label className={labelClass}>生成模式</label>
                <ThemedSelect
                  value={mode}
                  onChange={v => {
                    setMode(v as GenerationMode);
                    setImg2imgSourceMode('upload');
                    setSourceImage(null);
                    setSelectedHistoryObjectKey(null);
                    setResultImage(null);
                    setError(null);
                  }}
                  options={[
                    { value: 'txt2img', label: '文生图' },
                    { value: 'img2img', label: '图生图' },
                  ]}
                  className={selectClass}
                />
              </div>

              {/* Tool selector */}
              <div>
                <label className={labelClass}>{mode === 'img2img' ? '图生图模型' : '文生图模型'}</label>
                <ThemedSelect
                  value={selectedToolId ?? ''}
                  onChange={v => {
                    const id = Number(v);
                    setSelectedToolId(id);
                    const tool = availableTools.find(t => t.id === id);
                    const dim = tool?.provider === 'aliyun' ? 2048 : 1024;
                    setImgWidth(dim);
                    setImgHeight(dim);
                  }}
                  options={availableTools.map(t => ({
                    value: t.id,
                    label: (t.provider === 'openai' ? 'DALL-E' : t.provider === 'siliconflow' ? 'SiliconFlow' : t.provider === 'aliyun' ? '阿里云（千问）' : 'Stability AI') + (t.model ? ' / ' + t.model : ''),
                  }))}
                  className={selectClass}
                />
                {mode === 'img2img' && availableTools.length === 0 && (
                  <p className="text-xs text-amber-600 mt-1">
                    当前没有开启图生图的模型，请到模型配置页启用 support_img2img。
                  </p>
                )}
              </div>

              {mode === 'img2img' && (
                <div>
                  <label className={labelClass}>原图来源</label>
                  <ThemedSelect
                    value={img2imgSourceMode}
                    onChange={v => {
                      setImg2imgSourceMode(v as Img2ImgSourceMode);
                      setSourceImage(null);
                      setSelectedHistoryObjectKey(null);
                    }}
                    options={[
                      { value: 'upload', label: '上传文件' },
                      { value: 'history', label: '历史生成图' },
                    ]}
                    className={selectClass}
                  />
                </div>
              )}

              {mode === 'img2img' && img2imgSourceMode === 'upload' && (
                <div>
                  <label className={labelClass}>原图</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={e => setSourceImage(e.target.files?.[0] ?? null)}
                    className={inputClass}
                  />
                  {sourceImage && (
                    <p className="text-xs text-gray-500 mt-1">
                      已选择：{sourceImage.name}
                    </p>
                  )}
                </div>
              )}

              {mode === 'img2img' && img2imgSourceMode === 'history' && (
                <div>
                  <label className={labelClass}>历史生成图</label>
                  {loadingGeneratedImages ? (
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Loader2 size={14} className="animate-spin" />
                      加载中...
                    </div>
                  ) : generatedImages.length === 0 ? (
                    <p className="text-xs text-amber-600">暂无历史生成图，请先生成图片。</p>
                  ) : (
                    <div className="grid grid-cols-4 gap-2 max-h-44 overflow-y-auto p-1 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800">
                      {generatedImages.map((img) => {
                        const active = selectedHistoryObjectKey === img.object_key;
                        return (
                          <button
                            key={img.id}
                            type="button"
                            onClick={() => setSelectedHistoryObjectKey(img.object_key)}
                            className={`rounded-lg overflow-hidden border-2 transition ${
                              active ? 'border-cyan-400 shadow-md' : 'border-transparent hover:border-white/50'
                            }`}
                            title={img.prompt}
                          >
                            <img
                              src={img.thumbnail_url || img.image_url}
                              alt={img.prompt}
                              className="w-full h-20 object-cover"
                              loading="lazy"
                            />
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {selectedHistoryObjectKey && (
                    <p className="text-xs text-gray-500 mt-1">已选择历史图作为图生图输入</p>
                  )}
                </div>
              )}

              {/* Positive prompt */}
              <div>
                <label className={labelClass}>正向提示词</label>
                <textarea
                  value={positivePrompt}
                  onChange={e => setPositivePrompt(e.target.value)}
                  placeholder="high quality, detailed, photorealistic..."
                  rows={4}
                  className={inputClass + ' resize-none'}
                />
              </div>

              {/* Size */}
              <div>
                <label className={labelClass}>尺寸</label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {ASPECT_RATIO_PRESETS.map(preset => {
                    const isActive = imgWidth === preset.width && imgHeight === preset.height;
                    const maxBox = 14;
                    const ratio = preset.width / preset.height;
                    const bw = ratio >= 1 ? maxBox : Math.round(maxBox * ratio);
                    const bh = ratio < 1 ? maxBox : Math.round(maxBox / ratio);
                    return (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => { setImgWidth(preset.width); setImgHeight(preset.height); }}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
                          isActive
                            ? 'bg-gray-900 dark:bg-white border-gray-900 dark:border-white text-white dark:text-gray-900'
                            : 'bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-700 text-gray-600 hover:bg-gray-200 dark:hover:bg-zinc-600'
                        }`}
                      >
                        <div
                          className={`border-2 rounded-sm flex-shrink-0 ${isActive ? 'border-cyan-500' : 'border-gray-400'}`}
                          style={{ width: bw, height: bh }}
                        />
                        {preset.label}
                      </button>
                    );
                  })}
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1">
                    <label className="block text-xs text-gray-500 mb-1">宽度 (px)</label>
                    <input
                      type="number"
                      min={64}
                      max={4096}
                      step={64}
                      value={imgWidth}
                      onChange={e => setImgWidth(Math.max(64, Number(e.target.value)))}
                      className={inputClass}
                    />
                  </div>
                  <span className="text-gray-400 mt-5">×</span>
                  <div className="flex-1">
                    <label className="block text-xs text-gray-500 mb-1">高度 (px)</label>
                    <input
                      type="number"
                      min={64}
                      max={4096}
                      step={64}
                      value={imgHeight}
                      onChange={e => setImgHeight(Math.max(64, Number(e.target.value)))}
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerate}
                disabled={
                  isGenerating
                  || !selectedToolId
                  || !positivePrompt.trim()
                  || (
                    mode === 'img2img'
                    && (
                      (img2imgSourceMode === 'upload' && !sourceImage)
                      || (img2imgSourceMode === 'history' && !selectedHistoryObjectKey)
                    )
                  )
                }
                className="w-full py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl  hover:scale-[1.02] transition-all disabled:opacity-50 flex items-center justify-center gap-2 font-medium"
              >
                {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <ImageIcon size={18} />}
                {isGenerating ? (mode === 'img2img' ? '编辑中...' : '生成中...') : (mode === 'img2img' ? '编辑图片' : '生成图片')}
              </button>

              {error && (
                <div className="p-3 bg-red-100/30 border border-red-300/40 rounded-xl text-red-700 text-sm">
                  {error}
                </div>
              )}
            </div>

            {/* Right: Result */}
            <div className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 flex flex-col">
              <h3 className="text-sm font-medium text-gray-600 uppercase tracking-wide mb-4">生成结果</h3>
              {isGenerating ? (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 text-gray-500">
                  <Loader2 size={40} className="animate-spin text-gray-600 dark:text-zinc-300" />
                  <p className="text-sm">{mode === 'img2img' ? '正在编辑图像，请稍候...' : '正在生成图像，请稍候...'}</p>
                </div>
              ) : resultImage ? (
                <div className="flex-1 flex flex-col gap-4">
                  <div className="rounded-2xl overflow-hidden border border-gray-200 dark:border-zinc-800 shadow-lg">
                    <img src={resultImage} alt="生成结果" className="w-full object-contain" />
                  </div>
                  {revisedPrompt && (
                    <div className="p-3 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800">
                      <p className="text-xs text-gray-500 mb-1">AI 修订后的提示词：</p>
                      <p className="text-xs text-gray-700 leading-relaxed">{revisedPrompt}</p>
                    </div>
                  )}
                  <button
                    onClick={handleDownload}
                    className="flex items-center justify-center gap-2 py-2.5 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all text-sm"
                  >
                    <Download size={15} />
                    下载图片
                  </button>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 text-gray-400">
                  <div className="w-24 h-24 rounded-xl bg-gray-50 dark:bg-zinc-900 border-2 border-dashed border-gray-200 dark:border-zinc-700 flex items-center justify-center">
                    <ImageIcon size={36} className="opacity-40" />
                  </div>
                  <p className="text-sm">
                    {mode === 'img2img'
                      ? (img2imgSourceMode === 'history'
                        ? '选择历史图片并输入提示词后点击「编辑图片」'
                        : '上传原图并输入提示词后点击「编辑图片」')
                      : '输入提示词后点击「生成图片」'}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImageStudioPage;
