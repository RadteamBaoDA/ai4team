import re
import logging
from typing import Dict

try:
    from langdetect import detect as langdetect_detect
    from langdetect import DetectorFactory, LangDetectException

    DetectorFactory.seed = 0  # ensure deterministic results
    LANGDETECT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    langdetect_detect = None
    LangDetectException = Exception
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detect language from text and provide localized error messages."""
    LANGUAGE_PATTERNS = {
        'zh': {'patterns': [re.compile(r'[\u4e00-\u9fff]')], 'name': 'Chinese'},
        'vi': {'patterns': [re.compile(r'[\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0]')], 'name': 'Vietnamese'},
        'ja': {'patterns': [re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')], 'name': 'Japanese'},
        'ko': {'patterns': [re.compile(r'[\uac00-\ud7af]')], 'name': 'Korean'},
        'ru': {'patterns': [re.compile(r'[\u0400-\u04ff]')], 'name': 'Russian'},
        'ar': {'patterns': [re.compile(r'[\u0600-\u06ff]')], 'name': 'Arabic'},
    }
    LANGUAGE_ALIASES = {
        'zh-cn': 'zh',
        'zh-tw': 'zh',
        'pt-br': 'pt',
        'pt-pt': 'pt',
        'en-us': 'en',
        'en-gb': 'en',
    }
    SUPPORTED_LANG_CODES = {'en', 'zh', 'vi', 'ja', 'ko', 'ru', 'ar', 'fr', 'de', 'es', 'pt'}
    ENGLISH_PATTERN = re.compile(r'\b(the|a|an|and|or|is|are|was|were|be|have|has|had)\b', re.IGNORECASE)

    _BASE_MESSAGES = {
        'prompt_blocked': 'Your input was blocked by the security scanner. Reason: {reason}',
        'prompt_blocked_detail': 'Input contains unsafe content and cannot be processed.',
        'response_blocked': 'Model output was blocked by the security scanner.',
        'server_error': 'Internal server error.',
        'upstream_error': 'Upstream service error.',
        'server_busy': 'Server is currently busy processing other requests. Please try again later.',
        'request_timeout': 'Request timed out. Please try again with a shorter prompt or later.',
        'queue_full': 'Request queue is full. Server is currently overloaded.',
    }

    _TRANSLATIONS: Dict[str, Dict[str, str]] = {
        'zh': {
            'prompt_blocked': '您的输入因安全扫描被阻止。原因：{reason}',
            'prompt_blocked_detail': '输入包含不安全内容，无法处理。',
            'response_blocked': '模型输出被安全扫描阻止。',
            'server_error': '内部服务器错误。',
            'upstream_error': '上游服务发生错误。',
            'server_busy': '服务器正忙，请稍后再试。',
            'request_timeout': '请求超时，请稍后或缩短提示重试。',
            'queue_full': '请求队列已满，服务器过载。',
        },
        'vi': {
            'prompt_blocked': 'Yêu cầu của bạn đã bị chặn bởi trình quét bảo mật. Lý do: {reason}',
            'prompt_blocked_detail': 'Nội dung không an toàn nên không thể xử lý.',
            'response_blocked': 'Phản hồi bị chặn bởi trình quét bảo mật.',
            'server_error': 'Lỗi máy chủ nội bộ.',
            'upstream_error': 'Dịch vụ thượng nguồn gặp lỗi.',
            'server_busy': 'Máy chủ đang bận, vui lòng thử lại sau.',
            'request_timeout': 'Yêu cầu quá thời gian. Hãy thử lại sau hoặc rút ngắn nội dung.',
            'queue_full': 'Hàng đợi yêu cầu đã đầy, máy chủ đang quá tải.',
        },
        'ja': {
            'prompt_blocked': 'セキュリティスキャナーにより入力がブロックされました。理由: {reason}',
            'prompt_blocked_detail': '入力に安全でない内容が含まれているため処理できません。',
            'response_blocked': 'モデルの出力がセキュリティスキャナーによりブロックされました。',
            'server_error': 'サーバー内部エラーが発生しました。',
            'upstream_error': '上流サービスでエラーが発生しました。',
            'server_busy': 'サーバーが混雑しています。しばらくしてから再試行してください。',
            'request_timeout': 'タイムアウトしました。後でもう一度、または短いプロンプトでお試しください。',
            'queue_full': 'リクエストキューが満杯です。',
        },
        'ko': {
            'prompt_blocked': '보안 스캐너가 입력을 차단했습니다. 이유: {reason}',
            'prompt_blocked_detail': '입력에 안전하지 않은 내용이 포함되어 처리할 수 없습니다.',
            'response_blocked': '모델 출력이 보안 스캐너에 의해 차단되었습니다.',
            'server_error': '내부 서버 오류가 발생했습니다.',
            'upstream_error': '업스트림 서비스 오류가 발생했습니다.',
            'server_busy': '서버가 바쁘므로 잠시 후 다시 시도하세요.',
            'request_timeout': '요청 시간이 초과되었습니다. 프롬프트를 줄이거나 나중에 다시 시도하세요.',
            'queue_full': '요청 대기열이 가득 차 서버가 과부하 상태입니다.',
        },
        'ru': {
            'prompt_blocked': 'Ваш ввод заблокирован системой безопасности. Причина: {reason}',
            'prompt_blocked_detail': 'Ввод содержит небезопасный контент и не может быть обработан.',
            'response_blocked': 'Выход модели заблокирован системой безопасности.',
            'server_error': 'Внутренняя ошибка сервера.',
            'upstream_error': 'Ошибка во внешнем сервисе.',
            'server_busy': 'Сервер занят. Попробуйте позже.',
            'request_timeout': 'Время ожидания истекло. Попробуйте ещё раз позже или сократите запрос.',
            'queue_full': 'Очередь запросов заполнена. Сервер перегружен.',
        },
        'ar': {
            'prompt_blocked': 'تم حظر الإدخال بواسطة فحص الأمان. السبب: {reason}',
            'prompt_blocked_detail': 'يحتوي الإدخال على محتوى غير آمن ولا يمكن معالجته.',
            'response_blocked': 'تم حظر مخرجات النموذج بواسطة فحص الأمان.',
            'server_error': 'حدث خطأ داخلي في الخادم.',
            'upstream_error': 'حدث خطأ في الخدمة الخارجية.',
            'server_busy': 'الخادم مشغول حاليًا. يرجى المحاولة لاحقًا.',
            'request_timeout': 'انتهت مهلة الطلب. حاول مجددًا لاحقًا أو استخدم مطالبة أقصر.',
            'queue_full': 'قائمة الانتظار ممتلئة. الخادم مثقل بالطلبات.',
        },
        'fr': {
            'prompt_blocked': 'Votre requête a été bloquée par le scanner de sécurité. Raison : {reason}',
            'prompt_blocked_detail': 'La requête contient un contenu dangereux et ne peut pas être traitée.',
            'response_blocked': 'La réponse du modèle a été bloquée par le scanner de sécurité.',
            'server_error': 'Erreur interne du serveur.',
            'upstream_error': 'Erreur du service en amont.',
            'server_busy': 'Le serveur est occupé. Veuillez réessayer plus tard.',
            'request_timeout': 'Délai dépassé. Réessayez plus tard ou réduisez votre requête.',
            'queue_full': 'La file d’attente est pleine. Le serveur est surchargé.',
        },
        'de': {
            'prompt_blocked': 'Ihre Eingabe wurde vom Sicherheitsscanner blockiert. Grund: {reason}',
            'prompt_blocked_detail': 'Die Eingabe enthält unsichere Inhalte und kann nicht verarbeitet werden.',
            'response_blocked': 'Die Modellausgabe wurde vom Sicherheitsscanner blockiert.',
            'server_error': 'Interner Serverfehler.',
            'upstream_error': 'Fehler beim Upstream-Dienst.',
            'server_busy': 'Server ausgelastet. Bitte später erneut versuchen.',
            'request_timeout': 'Zeitüberschreitung. Versuchen Sie es später erneut oder verkürzen Sie die Eingabe.',
            'queue_full': 'Die Anfragenwarteschlange ist voll. Server überlastet.',
        },
        'es': {
            'prompt_blocked': 'Tu entrada fue bloqueada por el escáner de seguridad. Razón: {reason}',
            'prompt_blocked_detail': 'La entrada contiene contenido inseguro y no puede procesarse.',
            'response_blocked': 'La salida del modelo fue bloqueada por el escáner de seguridad.',
            'server_error': 'Error interno del servidor.',
            'upstream_error': 'Error en el servicio ascendente.',
            'server_busy': 'El servidor está ocupado. Inténtalo de nuevo más tarde.',
            'request_timeout': 'La solicitud agotó el tiempo. Intenta nuevamente más tarde o usa un mensaje más corto.',
            'queue_full': 'La cola de solicitudes está llena. El servidor está sobrecargado.',
        },
        'pt': {
            'prompt_blocked': 'Sua entrada foi bloqueada pelo verificador de segurança. Motivo: {reason}',
            'prompt_blocked_detail': 'A entrada contém conteúdo inseguro e não pode ser processada.',
            'response_blocked': 'A saída do modelo foi bloqueada pelo verificador de segurança.',
            'server_error': 'Erro interno do servidor.',
            'upstream_error': 'Erro no serviço upstream.',
            'server_busy': 'Servidor ocupado. Tente novamente mais tarde.',
            'request_timeout': 'Tempo limite atingido. Tente novamente mais tarde ou reduza o prompt.',
            'queue_full': 'A fila de solicitações está cheia. Servidor sobrecarregado.',
        },
    }

    ERROR_MESSAGES: Dict[str, Dict[str, str]] = {'en': _BASE_MESSAGES}
    for code in SUPPORTED_LANG_CODES:
        translations = _TRANSLATIONS.get(code)
        if translations:
            ERROR_MESSAGES[code] = {**_BASE_MESSAGES, **translations}
        else:
            ERROR_MESSAGES.setdefault(code, _BASE_MESSAGES)

    @staticmethod
    def detect_language(text: str) -> str:
        if not text:
            return 'en'

        # Quick regex-based detection for a handful of languages
        for lang_code, lang_info in LanguageDetector.LANGUAGE_PATTERNS.items():
            for pattern in lang_info['patterns']:
                if pattern.search(text):
                    logger.info("Detected language: %s", lang_info['name'])
                    return lang_code

        # Use langdetect if available for broader coverage
        if LANGDETECT_AVAILABLE and langdetect_detect is not None:
            try:
                detected = langdetect_detect(text)
                normalized = LanguageDetector.normalize_lang_code(detected)
                logger.debug("langdetect identified %s (normalized to %s)", detected, normalized)
                return normalized
            except LangDetectException as exc:  # pragma: no cover - library raises on short text
                logger.debug("langdetect failed: %s", exc)

        if LanguageDetector.ENGLISH_PATTERN.search(text):
            return 'en'
        return 'en'

    @staticmethod
    def normalize_lang_code(lang_code: str) -> str:
        if not lang_code:
            return 'en'
        lang_code = lang_code.lower()
        lang_code = LanguageDetector.LANGUAGE_ALIASES.get(lang_code, lang_code)
        base = lang_code.split('-')[0]
        if base in LanguageDetector.SUPPORTED_LANG_CODES:
            return base
        return 'en'

    @staticmethod
    def get_error_message(message_key: str, language: str, reason: str = '') -> str:
        messages = LanguageDetector.ERROR_MESSAGES.get(language, LanguageDetector.ERROR_MESSAGES['en'])
        message = messages.get(message_key, '')
        if reason and '{reason}' in message:
            message = message.format(reason=reason)
        return message


def get_language_message(text: str, message_key: str, reason: str = '') -> str:
    """Get localized error message based on detected language."""
    language = LanguageDetector.detect_language(text)
    return LanguageDetector.get_error_message(message_key, language, reason)
