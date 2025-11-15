"""
Advanced Chart Analysis Module
Integrates all 4 TradingView indicators with Plotly charts
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta

from indicators.volume_order_blocks import VolumeOrderBlocks
from indicators.htf_support_resistance import HTFSupportResistance
from indicators.htf_volume_footprint import HTFVolumeFootprint
from indicators.ultimate_rsi import UltimateRSI


class AdvancedChartAnalysis:
    """
    Advanced Chart Analysis with multiple technical indicators
    """

    def __init__(self):
        """Initialize Advanced Chart Analysis"""
        self.vob_indicator = VolumeOrderBlocks()
        self.htf_sr_indicator = HTFSupportResistance()
        self.htf_footprint = HTFVolumeFootprint()
        self.ultimate_rsi = UltimateRSI()

    def fetch_intraday_data(self, symbol, period='1d', interval='1m'):
        """
        Fetch intraday data using yfinance

        Args:
            symbol: Stock symbol (e.g., '^NSEI' for NIFTY)
            period: Period to fetch ('1d', '5d', '1mo')
            interval: Interval ('1m', '5m', '15m', '1h')

        Returns:
            DataFrame: OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if len(df) == 0:
                return None

            # Rename columns to lowercase
            df.columns = [col.lower() for col in df.columns]

            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                return None

            return df

        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def create_advanced_chart(self, df, symbol, show_vob=True, show_htf_sr=True,
                             show_footprint=True, show_rsi=True):
        """
        Create advanced chart with all indicators

        Args:
            df: DataFrame with OHLCV data
            symbol: Symbol name for title
            show_vob: Show Volume Order Blocks
            show_htf_sr: Show HTF Support/Resistance
            show_footprint: Show HTF Volume Footprint
            show_rsi: Show Ultimate RSI

        Returns:
            plotly Figure object
        """
        try:
            # Ensure dataframe has datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception as e:
                    raise ValueError(f"Unable to convert dataframe index to datetime: {e}")

            # Calculate all indicators
            vob_data = self.vob_indicator.calculate(df) if show_vob else None
            rsi_data = self.ultimate_rsi.get_signals(df) if show_rsi else None
        except Exception as e:
            raise Exception(f"Error calculating indicators: {str(e)}")

        # HTF Support/Resistance configuration
        htf_levels = []
        if show_htf_sr:
            levels_config = [
                {'timeframe': '4H', 'length': 4, 'style': 'Solid', 'color': '#26a69a'},
                {'timeframe': '12H', 'length': 5, 'style': 'Solid', 'color': '#2196f3'},
                {'timeframe': 'D', 'length': 5, 'style': 'Solid', 'color': '#9c27b0'},
                {'timeframe': 'W', 'length': 5, 'style': 'Solid', 'color': '#ff9800'}
            ]
            htf_levels = self.htf_sr_indicator.calculate_multi_timeframe(df, levels_config)

        # HTF Volume Footprint
        footprint_data = None
        if show_footprint:
            footprint_data = self.htf_footprint.calculate(df)

        # Create subplots
        if show_rsi:
            fig = make_subplots(
                rows=2, cols=1,
                row_heights=[0.7, 0.3],
                vertical_spacing=0.05,
                shared_xaxes=True,
                subplot_titles=(f'{symbol} - 1 Minute Chart', 'Ultimate RSI')
            )
        else:
            fig = make_subplots(
                rows=1, cols=1,
                subplot_titles=(f'{symbol} - 1 Minute Chart',)
            )

        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )

        # Add Volume Order Blocks
        if show_vob and vob_data:
            self._add_volume_order_blocks(fig, df, vob_data, row=1, col=1)

        # Add HTF Support/Resistance
        if show_htf_sr and htf_levels:
            self._add_htf_support_resistance(fig, df, htf_levels, row=1, col=1)

        # Add HTF Volume Footprint
        if show_footprint and footprint_data and footprint_data['current_footprint']:
            self._add_volume_footprint(fig, df, footprint_data, row=1, col=1)

        # Add Ultimate RSI
        if show_rsi and rsi_data:
            self._add_ultimate_rsi(fig, df, rsi_data, row=2, col=1)

        # Update layout
        fig.update_layout(
            title=f'{symbol} Advanced Chart Analysis',
            xaxis_title='Time',
            yaxis_title='Price',
            template='plotly_dark',
            height=800 if show_rsi else 600,
            showlegend=True,
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )

        return fig

    def _add_volume_order_blocks(self, fig, df, vob_data, row, col):
        """Add Volume Order Blocks to chart"""
        # Add EMA lines
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=vob_data['ema1'],
                mode='lines',
                name='EMA Fast',
                line=dict(color='#00bcd4', width=1),
                opacity=0.7
            ),
            row=row, col=col
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=vob_data['ema2'],
                mode='lines',
                name='EMA Slow',
                line=dict(color='#ff9800', width=1),
                opacity=0.7
            ),
            row=row, col=col
        )

        # Add bullish blocks
        for block in vob_data['bullish_blocks']:
            if block['active']:
                idx = block['index']
                if idx < len(df):
                    x_start = df.index[idx]
                    x_end = df.index[-1]

                    # Upper line
                    fig.add_trace(
                        go.Scatter(
                            x=[x_start, x_end],
                            y=[block['upper'], block['upper']],
                            mode='lines',
                            name=f"Bullish OB",
                            line=dict(color='#26ba9f', width=2),
                            showlegend=False
                        ),
                        row=row, col=col
                    )

                    # Lower line
                    fig.add_trace(
                        go.Scatter(
                            x=[x_start, x_end],
                            y=[block['lower'], block['lower']],
                            mode='lines',
                            line=dict(color='#26ba9f', width=2),
                            fill='tonexty',
                            fillcolor='rgba(38, 186, 159, 0.1)',
                            showlegend=False
                        ),
                        row=row, col=col
                    )

        # Add bearish blocks
        for block in vob_data['bearish_blocks']:
            if block['active']:
                idx = block['index']
                if idx < len(df):
                    x_start = df.index[idx]
                    x_end = df.index[-1]

                    # Upper line
                    fig.add_trace(
                        go.Scatter(
                            x=[x_start, x_end],
                            y=[block['upper'], block['upper']],
                            mode='lines',
                            name=f"Bearish OB",
                            line=dict(color='#6626ba', width=2),
                            showlegend=False
                        ),
                        row=row, col=col
                    )

                    # Lower line
                    fig.add_trace(
                        go.Scatter(
                            x=[x_start, x_end],
                            y=[block['lower'], block['lower']],
                            mode='lines',
                            line=dict(color='#6626ba', width=2),
                            fill='tonexty',
                            fillcolor='rgba(102, 38, 186, 0.1)',
                            showlegend=False
                        ),
                        row=row, col=col
                    )

    def _add_htf_support_resistance(self, fig, df, htf_levels, row, col):
        """Add HTF Support/Resistance levels to chart"""
        x_start = df.index[0]
        x_end = df.index[-1]

        for level in htf_levels:
            # Add pivot high
            if level['pivot_high'] is not None:
                fig.add_trace(
                    go.Scatter(
                        x=[x_start, x_end],
                        y=[level['pivot_high'], level['pivot_high']],
                        mode='lines',
                        name=f"{level['timeframe']} Resistance",
                        line=dict(color=level['color'], width=2, dash='dash'),
                        showlegend=True
                    ),
                    row=row, col=col
                )

            # Add pivot low
            if level['pivot_low'] is not None:
                fig.add_trace(
                    go.Scatter(
                        x=[x_start, x_end],
                        y=[level['pivot_low'], level['pivot_low']],
                        mode='lines',
                        name=f"{level['timeframe']} Support",
                        line=dict(color=level['color'], width=2, dash='dash'),
                        showlegend=True
                    ),
                    row=row, col=col
                )

    def _add_volume_footprint(self, fig, df, footprint_data, row, col):
        """Add HTF Volume Footprint to chart"""
        current = footprint_data['current_footprint']
        if not current:
            return

        # Add POC line
        x_start = df.index[0]
        x_end = df.index[-1]

        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[current['poc'], current['poc']],
                mode='lines',
                name='POC (Point of Control)',
                line=dict(color='#298ada', width=3, dash='dot'),
                showlegend=True
            ),
            row=row, col=col
        )

        # Add Value Area
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[current['value_area_high'], current['value_area_high']],
                mode='lines',
                name='Value Area High',
                line=dict(color='#64b5f6', width=1, dash='dot'),
                showlegend=False
            ),
            row=row, col=col
        )

        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[current['value_area_low'], current['value_area_low']],
                mode='lines',
                name='Value Area Low',
                line=dict(color='#64b5f6', width=1, dash='dot'),
                fill='tonexty',
                fillcolor='rgba(100, 181, 246, 0.1)',
                showlegend=False
            ),
            row=row, col=col
        )

    def _add_ultimate_rsi(self, fig, df, rsi_data, row, col):
        """Add Ultimate RSI indicator to chart"""
        # Add RSI line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=rsi_data['ultimate_rsi'],
                mode='lines',
                name='Ultimate RSI',
                line=dict(color='#00bcd4', width=2)
            ),
            row=row, col=col
        )

        # Add signal line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=rsi_data['signal'],
                mode='lines',
                name='Signal',
                line=dict(color='#ff5d00', width=2)
            ),
            row=row, col=col
        )

        # Add overbought/oversold lines
        fig.add_hline(y=80, line_dash="dash", line_color="red",
                     annotation_text="Overbought", row=row, col=col)
        fig.add_hline(y=20, line_dash="dash", line_color="green",
                     annotation_text="Oversold", row=row, col=col)
        fig.add_hline(y=50, line_dash="dot", line_color="gray",
                     annotation_text="Midline", row=row, col=col)

        # Update RSI yaxis
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=row, col=col)
