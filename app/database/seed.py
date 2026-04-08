"""
Seed данные - начальные вопросы/ответы для FAQ
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import FAQ
from app.core.logger import log


SEED_FAQS = [
    {
        'question_ru': 'Сколько стоит курс?',
        'question_en': 'How much does the course cost?',
        'answer_ru': (
            "💰 Стоимость нашего курса - 30 000 рублей.\n\n"
            "Мы предлагаем:\n"
            "• Полный доступ ко всем материалам\n"
            "• Поддержку куратора\n"
            "• Сертификат по окончании\n"
            "• Доступ к закрытому сообществу\n\n"
            "Также доступна рассрочка на 3, 6 или 12 месяцев!"
        ),
        'answer_en': (
            '💰 The course costs 30,000 rubles.\n\n'
            'We offer:\n'
            '• Full access to all materials\n'
            '• Curator support\n'
            '• Certificate upon completion\n'
            '• Access to private community\n\n'
            'Installment plans available for 3, 6, or 12 months!'
        ),
        'keywords': 'сколько,стоит,цена,стоимость,сколько стоит,цена курса,how much,cost,price'
    },
    {
        'question_ru': 'Как записаться на курс?',
        'question_en': 'How to enroll in the course?',
        'answer_ru': (
            '📝 Записаться на курс очень просто!\n\n'
            '1️⃣ Напишите "Хочу записаться" или оставьте ваш телефон\n'
            '2️⃣ Менеджер свяжется с вами в течение часа\n'
            '3️⃣ Обсудим детали и оформим запись\n'
            '4️⃣ Получите доступ к материалам\n\n'
            'Готовы начать? Просто напишите ваш контактный телефон! 📞'
        ),
        'answer_en': (
            '📝 Enrolling is very easy!\n\n'
            '1️⃣ Write "I want to enroll" or leave your phone number\n'
            '2️⃣ Manager will contact you within an hour\n'
            '3️⃣ We will discuss details and complete registration\n'
            '4️⃣ Get access to materials\n\n'
            'Ready to start? Just write your contact phone! 📞'
        ),
        'keywords': 'как,записаться,записаться на курс,регистрация,начать,записаться,how to enroll,register,enrollment'
    },
    {
        'question_ru': 'Есть ли рассрочка?',
        'question_en': 'Is there an installment plan?',
        'answer_ru': (
            "💳 Да! Мы предлагаем удобную рассрочку:\n\n"
            "• 3 месяца - 10 000 руб/мес\n"
            "• 6 месяцев - 5 000 руб/мес\n"
            "• 12 месяцев - 2 500 руб/мес\n\n"
            "✅ Без переплат и скрытых комиссий\n"
            "✅ Оформление за 5 минут\n"
            "✅ Первый платеж через 30 дней\n\n"
            "Хотите оформить рассрочку? Оставьте ваш телефон!"
        ),
        'answer_en': (
            "💳 Yes! We offer convenient installment plans:\n\n"
            "• 3 months - 10,000 rub/month\n"
            "• 6 months - 5,000 rub/month\n"
            "• 12 months - 2,500 rub/month\n\n"
            "✅ No overpayments or hidden fees\n"
            "✅ Registration in 5 minutes\n"
            "✅ First payment in 30 days\n\n"
            "Want to set up an installment? Leave your phone number!"
        ),
        'keywords': 'рассрочка,рассрочка на курс,платежи,оплата частями,installment,plan,payment'
    },
    {
        'question_ru': 'Что входит в курс?',
        'question_en': 'What is included in the course?',
        'answer_ru': (
            '📚 В курс входит:\n\n'
            '• 📹 50+ видеоуроков в записи\n'
            '• 📝 Практические задания с проверкой\n'
            '• 💬 Чат с куратором и студентами\n'
            '• 📖 Дополнительные материалы и чек-листы\n'
            '• 🎯 Домашние задания с обратной связью\n'
            '• 🏆 Сертификат по окончании\n'
            '• ♾️ Бессрочный доступ к материалам\n\n'
            'Хотите узнать подробнее? Спрашивайте!'
        ),
        'answer_en': (
            '📚 The course includes:\n\n'
            '• 📹 50+ recorded video lessons\n'
            '• 📝 Practical assignments with review\n'
            '• 💬 Chat with curator and students\n'
            '• 📖 Additional materials and checklists\n'
            '• 🎯 Homework with feedback\n'
            '• 🏆 Certificate upon completion\n'
            '• ♾️ Lifetime access to materials\n\n'
            'Want to know more? Just ask!'
        ),
        'keywords': 'что входит,содержание,программа,курса,материалы,included,program,content,materials'
    },
    {
        'question_ru': 'Сколько длится курс?',
        'question_en': 'How long is the course?',
        'answer_ru': (
            '⏱️ Длительность курса:\n\n'
            '• 📅 Основной курс: 8 недель\n'
            '• 📚 Самостоятельное изучение: в вашем темпе\n'
            '• ♾️ Доступ к материалам: бессрочно\n\n'
            'Рекомендуемая нагрузка: 5-7 часов в неделю'
        ),
        'answer_en': (
            '⏱️ Course duration:\n\n'
            '• 📅 Main course: 8 weeks\n'
            '• 📚 Self-study: at your own pace\n'
            '• ♾️ Access to materials: lifetime\n\n'
            'Recommended workload: 5-7 hours per week'
        ),
        'keywords': 'сколько,длится,длительность,время,сколько недель,how long,duration,time,weeks'
    },
    {
        'question_ru': 'Есть ли гарантия возврата денег?',
        'question_en': 'Is there a money-back guarantee?',
        'answer_ru': (
            '🛡️ Да! Мы предоставляем гарантию:\n\n'
            '• ✅ 14 дней на возврат без вопросов\n'
            '• ✅ Полный возврат стоимости\n'
            "• ✅ Без скрытых условий\n\n"
            "Если курс вам не подойдет - вернем деньги!"
        ),
        'answer_en': (
            "🛡️ Yes! We provide a guarantee:\n\n"
            "• ✅ 14 days no-questions-asked return\n"
            "• ✅ Full refund\n"
            "• ✅ No hidden conditions\n\n"
            "If the course doesn't work for you - we will refund your money!"
        ),
        'keywords': 'гарантия,возврат,деньги,refund,guarantee,money back,return'
    },
    {
        'question_ru': 'Где проходит обучение?',
        'question_en': 'Where does the training take place?',
        'answer_ru': (
            '💻 Обучение проходит онлайн:\n\n'
            '• 📱 Удобная платформа для обучения\n'
            '• 🌍 Доступ из любой точки мира\n'
            '• ⏰ Учитесь в удобное время\n'
            '• 📹 Все уроки в записи\n\n'
            'Нужен только интернет и желание учиться!'
        ),
        'answer_en': (
            '💻 Training takes place online:\n\n'
            '• 📱 Convenient learning platform\n'
            '• 🌍 Access from anywhere in the world\n'
            '• ⏰ Learn at your convenience\n'
            '• 📹 All lessons are recorded\n\n'
            'All you need is internet and desire to learn!'
        ),
        'keywords': 'где,проходит,обучение,онлайн,платформа,where,online,platform,training'
    },
    {
        'question_ru': 'Получу ли я сертификат?',
        'question_en': 'Will I receive a certificate?',
        'answer_ru': (
            '🏆 Да! По окончании курса вы получите:\n\n'
            '• 📜 Именной сертификат в электронном виде\n'
            '• 📊 С указанием пройденных модулей\n'
            '• 🔗 Ссылку для проверки подлинности\n\n'
            'Сертификат можно добавить в резюме или портфолио!'
        ),
        'answer_en': (
            '🏆 Yes! Upon completion you will receive:\n\n'
            '• 📜 Named certificate in electronic format\n'
            '• 📊 With completed modules listed\n'
            '• 🔗 Link for authenticity verification\n\n'
            'Certificate can be added to your resume or portfolio!'
        ),
        'keywords': 'сертификат,диплом,документ,подтверждение,certificate,diploma,document'
    },
    {
        'question_ru': 'Какие способы оплаты доступны?',
        'question_en': 'What payment methods are available?',
        'answer_ru': (
            '💳 Доступные способы оплаты:\n\n'
            '• 💳 Банковская карта (Visa, MasterCard, МИР)\n'
            '• 🏦 Банковский перевод\n'
            '• 📱 СБП (Система быстрых платежей)\n'
            '• 💰 ЮMoney, QIWI\n'
            "• 📋 Рассрочка от банков-партнеров\n\n"
            "Оплата в рублях. Для юрлиц - безналичный расчет."
        ),
        'answer_en': (
            '💳 Available payment methods:\n\n'
            '• 💳 Bank card (Visa, MasterCard)\n'
            '• 🏦 Bank transfer\n'
            '• 📱 Fast payment system\n'
            '• 💰 Electronic wallets\n'
            '• 📋 Installment from partner banks\n\n'
            'Payment in rubles.'
        ),
        'keywords': 'оплата,способы,карта,перевод,как оплатить,payment,methods,card,bank'
    },
    {
        'question_ru': 'Нужна ли подготовка для курса?',
        'question_en': 'Is any preparation required for the course?',
        'answer_ru': (
            '🎯 Специальная подготовка не требуется!\n\n'
            'Курс подходит для:\n'
            '• ✅ Полных новичков\n'
            '• ✅ Тех, кто хочет систематизировать знания\n'
            '• ✅ Специалистов, желающих повысить квалификацию\n\n'
            'Мы объясняем всё простым языком с примерами!'
        ),
        'answer_en': (
            '🎯 No special preparation required!\n\n'
            'The course is suitable for:\n'
            '• ✅ Complete beginners\n'
            '• ✅ Those who want to systematize knowledge\n'
            '• ✅ Professionals wishing to improve qualifications\n\n'
            'We explain everything in simple language with examples!'
        ),
        'keywords': 'подготовка,требования,новичок,опыт,preparation,requirements,beginner,experience'
    }
]


async def seed_faqs(db_session: AsyncSession) -> int:
    """
    Заполнение базы данных начальными FAQ
    
    Returns:
        int: количество добавленных записей
    """
    from sqlalchemy import select
    
    # Проверяем, есть ли уже FAQ в базе
    result = await db_session.execute(select(FAQ))
    existing_faqs = result.scalars().all()
    
    if existing_faqs:
        log.info(f"FAQs already exist in database ({len(existing_faqs)} records). Skipping seed.")
        return 0
    
    # Добавляем seed данные
    count = 0
    for faq_data in SEED_FAQS:
        faq = FAQ(**faq_data)
        db_session.add(faq)
        count += 1
    
    await db_session.commit()
    log.info(f"Seeded {count} FAQs into database")
    return count
