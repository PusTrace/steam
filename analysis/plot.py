from datetime import datetime, timedelta, timezone
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def plot_analysis(raw_history, cleaned_history, slope_6m_data, slope_1m_data, save_path=None):

    """
    Визуализация истории цен: очистка + линейные регрессии (последний год)
    
    Args:
        raw_history: исходная история ДО очистки
        slope_6m_data: tuple (slope, intercept, x, y) для 6-месячной регрессии
        slope_1m_data: tuple (slope, intercept, x, y) для 1-месячной регрессии
        save_path: путь для сохранения графика (если None — показывает на экране)
    """
    
    logger = logging.getLogger("plot_analysis")
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    

    fig, ax = plt.subplots(1, 1, figsize=(16, 8))

    fig.suptitle('Price History Analysis (Last 12 Months)', fontsize=16, fontweight='bold')
    
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)
    

    raw_filtered = [(dt, price) for dt, price, _ in raw_history if dt >= one_year_ago]
    raw_dates = [r[0] for r in raw_filtered]
    raw_prices = [r[1] for r in raw_filtered]
    
    cleaned_filtered = [(dt, price) for dt, price, _ in cleaned_history if dt >= one_year_ago]
    cleaned_dates = [r[0] for r in cleaned_filtered]
    cleaned_prices = [r[1] for r in cleaned_filtered]
    
    ax.scatter(raw_dates, raw_prices, 
            alpha=0.5,
            s=5,   
            c='red', 
            label='Raw data (outliers included)',
            marker='o')
    
    
    ax.scatter(cleaned_dates, cleaned_prices, 
            alpha=0.75,        
            s=5,                 
            c='blue', 
            label='Cleaned data (IQR filtered)',
            marker='o',
            zorder=5)            # zorder — порядок слоёв (больше = выше)

    if slope_6m_data:
        slope_6m, intercept_6m, x_6m, y_6m = slope_6m_data
        
        start_date_6m = now - timedelta(days=180)

        regression_dates_6m = [start_date_6m + timedelta(days=float(xi)) for xi in x_6m]
        
        # y = slope * x + intercept
        regression_prices_6m = slope_6m * x_6m + intercept_6m
        
        # Фильтруем только последний год для отображения
        filtered_6m = [(d, p) for d, p in zip(regression_dates_6m, regression_prices_6m) 
                    if d >= one_year_ago]
        if filtered_6m:
            dates_6m, prices_6m = zip(*filtered_6m)
            ax.plot(dates_6m, prices_6m, 
                linestyle='--',          # пунктирная линия
                linewidth=2.5, 
                color='darkred',
                alpha=0.8,
                label=f'6-month trend (slope={slope_6m:.4f})',
                zorder=10)
    
    # 1-месячная регрессия
    if slope_1m_data:
        slope_1m, intercept_1m, x_1m, y_1m = slope_1m_data
        
        start_date_1m = now - timedelta(days=30)
        regression_dates_1m = [start_date_1m + timedelta(days=float(xi)) for xi in x_1m]
        regression_prices_1m = slope_1m * x_1m + intercept_1m
        
        one_week_ago = now - timedelta(days=7)
        
        # 1-месячная всегда в пределах года, фильтровать не нужно
        ax.plot(regression_dates_1m, regression_prices_1m, 
            linestyle='-',               # сплошная линия
            linewidth=3, 
            color='green',
            alpha=0.9,
            label=f'1-month trend (slope={slope_1m:.4f})',
            zorder=11)                   # самый верхний слой
    
    ax.axvline(one_week_ago, 
            color='orange', 
            linestyle=':', 
            alpha=0.6, 
            linewidth=1.5,
            label='1 week ago')
    
    ax.axvline(start_date_1m, 
            color='purple', 
            linestyle=':', 
            alpha=0.6, 
            linewidth=1.5,
            label='1 month ago')
    

    ax.set_title('Price Trends & Outlier Removal', fontsize=13, fontweight='bold', pad=15)
    
    ax.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax.set_ylabel('Price (₸)', fontsize=11, fontweight='bold')
    
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    

    plt.setp(ax.xaxis.get_majorticklabels(), 
            rotation=45,
            ha='right',
            fontsize=9)
    

    ax.legend(loc='upper left', fontsize=10, framealpha=0.9, edgecolor='black')
    
    ax.set_xlim(one_year_ago, now)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches='tight')
        logger.info(f"Plot saved to: {save_path}")
    else:
        plt.show()
    
    plt.close()