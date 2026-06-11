from loader import bot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.user_service import get_or_create_user
from database.history_service import save_search_history
from api.kinopoisk_api import KinopoiskAPI
from utils.logger import logger

api = KinopoiskAPI()

# Временное хранилище — заменить на Redis в Фазе 1
user_search_results: dict = {}
user_search_queries: dict = {}


@bot.message_handler(commands=["search"])
def search_movie_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(
            message,
            "🔍 *Как искать:*\n`/search Название фильма`\n\nПример: `/search Интерстеллар`",
            parse_mode="Markdown",
        )
        return

    query = parts[1].strip()
    user = get_or_create_user(message)
    wait = bot.reply_to(message, f"🔍 Ищу: *{query}*...", parse_mode="Markdown")

    result = api.search_movie(query, limit=8)
    movies = result.get("movies", [])

    if not movies:
        bot.edit_message_text(
            f"😔 По запросу *{query}* ничего не найдено.\n\nПопробуйте другое название.",
            chat_id=wait.chat.id,
            message_id=wait.message_id,
            parse_mode="Markdown",
        )
        save_search_history(message, query)
        return

    user_search_results[user.user_id] = movies
    user_search_queries[user.user_id] = query

    markup = _build_list_markup(user.user_id, movies)
    bot.edit_message_text(
        f"✅ Найдено *{len(movies)}* по запросу *{query}*.\nВыберите фильм:",
        chat_id=wait.chat.id,
        message_id=wait.message_id,
        reply_markup=markup,
        parse_mode="Markdown",
    )
    save_search_history(message, query)


@bot.callback_query_handler(func=lambda c: c.data.startswith("movie_"))
def handle_movie_selection(call):
    parts = call.data.split("_")
    user_id, movie_index = int(parts[1]), int(parts[2])

    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Это не ваш результат!", show_alert=True)
        return

    movies = user_search_results.get(user_id, [])
    if movie_index >= len(movies):
        bot.answer_callback_query(call.id, "Результаты устарели, найдите снова", show_alert=True)
        return

    movie = movies[movie_index]
    text = _format_movie_card(movie)

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔙 Назад", callback_data=f"back_{user_id}"),
        InlineKeyboardButton("❤️ Вишлист", callback_data=f"wish_{movie.get('id')}"),
    )
    if movie.get("poster"):
        markup.add(InlineKeyboardButton(
            "🖼 Постер",
            callback_data=f"poster_{movie.get('id')}_{user_id}_{movie_index}",
        ))

    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown",
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("poster_"))
def handle_poster(call):
    parts = call.data.split("_")
    user_id = int(parts[2])
    movie_index = int(parts[3])

    movies = user_search_results.get(user_id, [])
    if movie_index < len(movies):
        poster_url = movies[movie_index].get("poster")
        if poster_url:
            bot.send_photo(call.message.chat.id, poster_url)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("back_"))
def handle_back(call):
    user_id = int(call.data.split("_")[1])
    movies = user_search_results.get(user_id, [])
    query = user_search_queries.get(user_id, "предыдущий запрос")

    if not movies:
        bot.answer_callback_query(call.id, "Результаты устарели, выполните поиск снова", show_alert=True)
        return

    markup = _build_list_markup(user_id, movies)
    bot.edit_message_text(
        f"✅ Результаты по запросу *{query}*:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown",
    )
    bot.answer_callback_query(call.id)


def _build_list_markup(user_id: int, movies: list) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    for i, movie in enumerate(movies):
        title = movie.get("title", "Без названия")
        year = f" ({movie['year']})" if movie.get("year") else ""
        r_val = float(movie.get("rating") or 0)
        rating = f" ⭐{r_val:.1f}" if r_val > 0 else ""
        icon = "📺" if movie.get("type") == "tv-series" else "🎬"
        markup.add(InlineKeyboardButton(
            f"{icon} {title}{year}{rating}",
            callback_data=f"movie_{user_id}_{i}",
        ))
    return markup


def _format_movie_card(movie: dict) -> str:
    title = movie.get("title", "Без названия")
    year = movie.get("year", "?")
    r_val = float(movie.get("rating") or 0)
    rating = f"{r_val:.1f}" if r_val > 0 else "Н/Д"
    r_emoji = "🟢" if r_val >= 7 else "🟡" if r_val >= 5 else "🔴"
    genres = ", ".join(movie.get("genres", [])) or "Не указан"
    desc = (movie.get("description") or "Описание недоступно")[:400]
    type_label = "📺 Сериал" if movie.get("type") == "tv-series" else "🎬 Фильм"

    return (
        f"{type_label}: *{title}* ({year})\n"
        f"{r_emoji} Рейтинг КП: *{rating}*\n"
        f"🎭 Жанр: {genres}\n\n"
        f"📖 {desc}..."
    )
