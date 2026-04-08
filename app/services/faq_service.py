"""
Сервис для работы с FAQ и кэшированием
"""
from typing import Optional, List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import re
from app.database.models import FAQ
from app.services.redis_client import redis_client
from app.core.settings import settings
from app.core.logger import log


class FAQService:
    """Сервис для работы с FAQ"""
    
    CACHE_PREFIX = "faq:"
    CACHE_KEY_ALL = "faq:all"
    
    # Слова-стопы для фильтрации
    STOP_WORDS_RU = {
        'сколько', 'стоит', 'цена', 'дорого', 'дешево', 'скидка',
        'как', 'записаться', 'начать', 'купить', 'оплатить',
        'что', 'входит', 'курсе', 'программа', 'содержание',
        'рассрочка', 'возврат', 'деньги', 'гарантия',
        'когда', 'начало', 'длительность', 'время', 'сколько',
        'где', 'проходит', 'онлайн', 'офлайн',
        'сертификат', 'диплом', 'документ'
    }
    
    STOP_WORDS_EN = {
        'how', 'much', 'cost', 'price', 'expensive', 'cheap', 'discount',
        'enroll', 'register', 'start', 'buy', 'pay',
        'what', 'included', 'course', 'program', 'content',
        'installment', 'refund', 'money', 'guarantee',
        'when', 'begin', 'duration', 'time',
        'where', 'online', 'offline',
        'certificate', 'diploma'
    }
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}  # In-memory cache как fallback
    
    def _detect_language(self, text: str) -> str:
        """Определение языка сообщения (улучшенный метод)"""
        # Считаем русские и английские буквы
        ru_chars = len(re.findall('[а-яА-ЯёЁ]', text))
        en_chars = len(re.findall('[a-zA-Z]', text))
        
        # Если русских букв больше или текст смешанный но есть русские
        if ru_chars > en_chars or (ru_chars > 0 and ru_chars >= en_chars * 0.3):
            return 'ru'
        return 'en'
    
    def _extract_keywords_from_message(self, message: str) -> List[str]:
        """Извлечение ключевых слов из сообщения пользователя"""
        message_lower = message.lower()
        stop_words = self.STOP_WORDS_RU if self._detect_language(message) == 'ru' else self.STOP_WORDS_EN
        
        # Разбиваем на слова и фильтруем стоп-слова
        words = re.findall(r'[а-яА-Яa-zA-Z]{3,}', message_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _calculate_keyword_score(self, message: str, faq_keywords: List[str]) -> float:
        """Расчет scores по совпадению ключевых слов"""
        message_lower = message.lower()
        message_words = set(re.findall(r'[а-яА-Яa-zA-Z]{2,}', message_lower))
        
        if not message_words:
            return 0.0
        
        matched_keywords = 0
        total_weight = 0
        
        for keyword in faq_keywords:
            keyword = keyword.strip().lower()
            if not keyword:
                continue
            
            # Проверяем точное совпадение
            if keyword in message_lower:
                matched_keywords += 1
                total_weight += len(keyword)  # Более длинные ключевые слова весят больше
            
            # Проверяем частичное совпадение (для длинных ключевых слов)
            elif len(keyword) > 5:
                keyword_parts = keyword.split()
                for part in keyword_parts:
                    if len(part) > 3 and part in message_lower:
                        matched_keywords += 0.5
                        total_weight += len(part) * 0.5
        
        if not faq_keywords:
            return 0.0
        
        # Нормализуем score
        score = (matched_keywords * 10 + total_weight) / (len(faq_keywords) * 10)
        return min(score, 1.0)
    
    def _calculate_question_similarity(self, message: str, faq_question: str) -> float:
        """Расчет схожести с вопросом FAQ"""
        message_words = set(re.findall(r'[а-яА-Яa-zA-Z]{3,}', message.lower()))
        question_words = set(re.findall(r'[а-яА-Яa-zA-Z]{3,}', faq_question.lower()))
        
        if not message_words or not question_words:
            return 0.0
        
        intersection = message_words.intersection(question_words)
        union = message_words.union(question_words)
        
        # Jaccard similarity
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Дополнительно: если все слова из вопроса есть в сообщении
        if question_words.issubset(message_words):
            return max(jaccard, 0.8)
        
        return jaccard
    
    async def get_all_faqs(self, db_session: AsyncSession) -> List[Dict]:
        """Получить все FAQ (с кэшированием)"""
        # Проверяем Redis кэш
        cached = await redis_client.get(self.CACHE_KEY_ALL)
        if cached:
            log.debug("FAQ cache HIT (Redis)")
            return cached
        
        # Проверяем in-memory кэш
        if self._cache.get(self.CACHE_KEY_ALL):
            log.debug("FAQ cache HIT (memory)")
            return self._cache[self.CACHE_KEY_ALL]
        
        # Запрос к БД
        result = await db_session.execute(
            select(FAQ).where(FAQ.is_active == True)
        )
        faqs = result.scalars().all()
        
        # Кэшируем
        faqs_data = []
        for faq in faqs:
            faq_dict = {
                'id': faq.id,
                'question_ru': faq.question_ru,
                'question_en': faq.question_en,
                'answer_ru': faq.answer_ru,
                'answer_en': faq.answer_en,
                'keywords': [k.strip() for k in faq.keywords.split(',') if k.strip()],
                'usage_count': faq.usage_count
            }
            faqs_data.append(faq_dict)
        
        await redis_client.set(self.CACHE_KEY_ALL, faqs_data, settings.FAQ_CACHE_TTL)
        self._cache[self.CACHE_KEY_ALL] = faqs_data
        
        log.info(f"Loaded {len(faqs)} FAQs from database")
        return faqs_data
    
    async def find_answer(self, user_message: str, db_session: AsyncSession) -> Optional[Dict]:
        """Поиск ответа на вопрос (улучшенный алгоритм)"""
        language = self._detect_language(user_message)
        message_lower = user_message.lower()
        
        # Получаем все FAQ
        faqs = await self.get_all_faqs(db_session)
        
        if not faqs:
            log.warning("No FAQs in database")
            return None
        
        best_match = None
        best_score = 0.0
        threshold = 0.15  # Минимальный порог схожести
        
        for faq in faqs:
            keywords = faq['keywords']
            question = faq['question_ru'] if language == 'ru' else faq['question_en']
            
            # Score 1: Совпадение ключевых слов
            keyword_score = self._calculate_keyword_score(user_message, keywords)
            
            # Score 2: Схожесть с вопросом
            question_similarity = self._calculate_question_similarity(user_message, question)
            
            # Комбинированный score (60% keywords, 40% question similarity)
            combined_score = keyword_score * 0.6 + question_similarity * 0.4
            
            # Бонус за точное вхождение ключевого слова
            for keyword in keywords:
                if keyword.strip().lower() in message_lower:
                    combined_score += 0.1
            
            if combined_score > best_score and combined_score > threshold:
                best_score = combined_score
                best_match = faq
        
        if best_match:
            # Увеличиваем счетчик использований
            await self.increment_usage(best_match['id'], db_session)
            
            answer = best_match['answer_ru'] if language == 'ru' else best_match['answer_en']
            log.info(f"FAQ match found (score: {best_score:.2f}, language: {language}, faq_id: {best_match['id']})")
            
            return {
                'answer': answer,
                'faq_id': best_match['id'],
                'language': language,
                'score': best_score
            }
        
        log.debug(f"No FAQ match found for: {user_message[:50]}")
        return None
    
    async def increment_usage(self, faq_id: int, db_session: AsyncSession):
        """Увеличение счетчика использования FAQ"""
        try:
            result = await db_session.execute(
                select(FAQ).where(FAQ.id == faq_id)
            )
            faq = result.scalar_one_or_none()
            
            if faq:
                faq.usage_count += 1
                await db_session.commit()
                
                # Инвалидируем кэш
                await redis_client.delete(self.CACHE_KEY_ALL)
                if self.CACHE_KEY_ALL in self._cache:
                    del self._cache[self.CACHE_KEY_ALL]
                
                log.debug(f"FAQ #{faq_id} usage incremented: {faq.usage_count}")
        except Exception as e:
            log.error(f"Error incrementing FAQ usage: {e}")
            await db_session.rollback()
    
    async def add_faq(
        self,
        db_session: AsyncSession,
        question_ru: str,
        question_en: str,
        answer_ru: str,
        answer_en: str,
        keywords: str
    ) -> FAQ:
        """Добавление нового FAQ"""
        try:
            faq = FAQ(
                question_ru=question_ru,
                question_en=question_en,
                answer_ru=answer_ru,
                answer_en=answer_en,
                keywords=keywords
            )
            
            db_session.add(faq)
            await db_session.commit()
            await db_session.refresh(faq)
            
            # Инвалидируем кэш
            await self.clear_cache()
            
            log.info(f"FAQ added: #{faq.id}")
            return faq
            
        except Exception as e:
            log.error(f"Error adding FAQ: {e}")
            await db_session.rollback()
            raise
    
    async def delete_faq(self, db_session: AsyncSession, faq_id: int) -> bool:
        """Удаление FAQ"""
        try:
            result = await db_session.execute(
                select(FAQ).where(FAQ.id == faq_id)
            )
            faq = result.scalar_one_or_none()
            
            if faq:
                await db_session.delete(faq)
                await db_session.commit()
                
                # Инвалидируем кэш
                await self.clear_cache()
                
                log.info(f"FAQ deleted: #{faq_id}")
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Error deleting FAQ: {e}")
            await db_session.rollback()
            raise
    
    async def clear_cache(self):
        """Очистка кэша FAQ"""
        await redis_client.delete(self.CACHE_KEY_ALL)
        self._cache.clear()
        log.info("FAQ cache cleared")


# Глобальный экземпляр
faq_service = FAQService()
