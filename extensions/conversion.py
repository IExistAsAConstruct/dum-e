from typing import Optional

import hikari
import lightbulb

convert_plugin = lightbulb.Plugin("Conversion")


@convert_plugin.command
@lightbulb.command("convert", "Convert from one unit to another.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def convert(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond("invoked convert")
    
@convert.child
@lightbulb.option("from_unit", "What unit to convert from.", type=str, choices=["Celsius", "Fahrenheit", "Kelvin", "Rankine"])
@lightbulb.option("to_unit", "What unit to convert into.", type=str, choices=["Celsius", "Fahrenheit", "Kelvin", "Rankine"])
@lightbulb.option("rounding", "How many decimal places to round. Defaults to 2.", type=int, default=2, required=False)
@lightbulb.option("value", "The value of the digit that you want to convert.", type=float)
@lightbulb.command("temperature", "Convert temperature into different units.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def temperature(ctx: lightbulb.Context, from_unit: str, to_unit: str, value: float, rounding: int = 2) -> None:
    if to_unit == from_unit:
        await ctx.respond("You cannot convert into the same type of unit!")
        return
        
    unit_shortcuts = {"Celsius": "°C", "Fahrenheit": "°F", "Kelvin": "K", "Rankine": "°R"}
    
    units = {
        "Celsius": {
            "Fahrenheit": lambda x: (x * 9/5) + 32,
            "Kelvin": lambda x: x + 273.15,
            "Rankine": lambda x: (x + 273.15) * 9/5
        },
        "Fahrenheit": {
            "Celsius": lambda x: (x - 32) * 5/9,
            "Kelvin": lambda x: (x + 459.67) * 5/9,
            "Rankine": lambda x: x + 459.67
        },
        "Kelvin": {
            "Celsius": lambda x: x - 273.15,
            "Fahrenheit": lambda x: (x * 9/5) - 459.67,
            "Rankine": lambda x: x * 9/5
        },
        "Rankine": {
            "Celsius": lambda x: (x - 491.67) * 5/9,
            "Fahrenheit": lambda x: x - 459.67,
            "Kelvin": lambda x: x * 5/9
        }
    }
        
    conversion = round(units[from_unit][to_unit](value), rounding)
    
    await ctx.respond(f"{value} {unit_shortcuts[from_unit]} is equal to {conversion} {unit_shortcuts[to_unit]}.")
    
@convert.child
@lightbulb.option("from_unit", "What unit to convert from.", type=str, choices=["Kilogram", "Ounce", "Pound", "Stone", "Short Ton", "Long Ton"])
@lightbulb.option("to_unit", "What unit to convert into.", type=str, choices=["Kilogram", "Ounce", "Pound", "Stone", "Short Ton", "Long Ton"])
@lightbulb.option("rounding", "How many decimal places to round. Defaults to 2.", type=int, default=2, required=False)
@lightbulb.option("value", "The value of the digit that you want to convert.", type=float)
@lightbulb.command("mass", "Convert mass into different units.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def mass(ctx: lightbulb.Context, from_unit: str, to_unit: str, value: float, rounding: int = 2) -> None:
    if to_unit == from_unit:
        await ctx.respond("You cannot convert into the same type of unit!")
        return
        
    unit_shortcuts = {"Kilogram": "kg", "Ounce": "oz", "Pound": "lbs", "Stone": "st", "Short Ton": "ST", "Long Ton": "LT"}
    
    # standardized to the pound
    units = {
        "Kilogram": 2.204623,
        "Ounce": 0.0625,
        "Pound": 1,
        "Stone": 14,
        "Short Ton": 2000,
        "Long Tom": 2240
    }
    
    conversion = round(value * units[from_unit] / units[to_unit], rounding)
    
    await ctx.respond(f"{value} {unit_shortcuts[from_unit]} is equal to {conversion} {unit_shortcuts[to_unit]}.")
    
@convert.child
@lightbulb.option("from_unit", "What unit to convert from.", type=str, choices=["Meter", "Inch", "Foot", "Yard", "Chain", "Hand", "Horse Length", "Furlong", "Mile", "League (Land)", "Fathom", "Naut Mile", "Smoot", "Double-Decker Bus", "Football Field"])
@lightbulb.option("to_unit", "What unit to convert into.", type=str, choices=["Meter", "Inch", "Foot", "Yard", "Chain", "Hand", "Horse Length", "Furlong", "Mile", "League (Land)", "Fathom", "Naut Mile", "Smoot", "Double-Decker Bus", "Football Field"])
@lightbulb.option("rounding", "How many decimal places to round. Defaults to 2.", type=int, default=2, required=False)
@lightbulb.option("value", "The value of the digit that you want to convert.", type=float)
@lightbulb.command("length", "Convert length into different units.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def length(ctx: lightbulb.Context, from_unit: str, to_unit: str, value: float, rounding: int = 2) -> None:
    if from_unit == to_unit:
        await ctx.respond("You cannot convert into the same type of unit!")
        return
        
    unit_shortcuts = {"Meter": "m", "Inch": "in", "Foot": "ft", "Yard": "yd", "Chain": "ch", "Hand": "h", "Horse Length": "horse lengths", "Furlong": "furlongs", "Mile": "mi", "League (Land)": "leagues", "Fathom": "fathoms", "Naut Mile": "nmi", "Smoot": "smoots", "Double-Decker Bus": "double-decker buses", "Football Field": "football fields"}
    
    # standardized to the yard
    units = {
        "Meter": 1.093613,
        "Inch": 0.027778,
        "Feet": 0.333333,
        "Yard": 1,
        "Chain": 22,
        "Hand": 0.111112,
        "Horse Length": 2.666664,
        "Furlong": 220,
        "Mile": 1760,
        "League (Land)": 5280,
        "Fathom": 1.999998,
        "Naut Mile": 2025.371276,
        "Smoot": 2.0331819694073,
        "Double-Decker Bus": 11.55948941,
        "Football Field": 120
    }
    
    conversion = round(value * units[from_unit] / units[to_unit], rounding)
    
    await ctx.respond(f"{value} {unit_shortcuts[from_unit]} is equal to {conversion} {unit_shortcuts[to_unit]}.")
    
@convert.child
@lightbulb.option("from_unit", "What unit to convert from.", type=str, choices=["Milliliter", "Liter", "Cubic Meter", "Fluid Dram", "Teaspoon", "Tablespoon", "Cubic Inch", "Fluid Ounce", "Shot", "Cup", "Pint", "Quart", "Pottle", "Gallon", "Cubic Feet", "Barrel", "Butt", "Cubic Yard"])
@lightbulb.option("to_unit", "What unit to convert into.", type=str, choices=["Milliliter", "Liter", "Cubic Meter", "Fluid Dram", "Teaspoon", "Tablespoon", "Cubic Inch", "Fluid Ounce", "Shot", "Cup", "Pint", "Quart", "Pottle", "Gallon", "Cubic Feet", "Barrel", "Butt", "Cubic Yard"])
@lightbulb.option("rounding", "How many decimal places to round. Defaults to 2.", type=int, default=2, required=False)
@lightbulb.option("value", "The value of the digit that you want to convert.", type=float)
@lightbulb.command("volume", "Convert length into different units.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def volume(ctx: lightbulb.Context, from_unit: str, to_unit: str, value: float, rounding: int = 2) -> None:
    if from_unit == to_unit:
        await ctx.respond("You cannot convert into the same type of unit!")
        return
        
    unit_shortcuts = {"Milliliter": "mL", "Liter": "L", "Cubic Meter": "m³", "Fluid Dram": "fl dr", "Teaspoon": "tsp", "Tablespoon": "tbsp", "Cubic Inch": "in³", "Fluid Ounce": "fl oz", "Shot": "jigs", "Cup": "cups", "Pint": "pt", "Quart": "qt", "Pottle": "pot", "Gallon": "gal", "Cubic Feet": "ft³", "Barrel": "bbl", "Butt": "butts", "Cubic Yard": "yd³"}
    
    #standardized to the fluid ounce
    units = {
        "Milliliter": 0.033814022701843,
        "Liter": 33.814022701843,
        "Cubic Meter": 33814.02,
        "Fluid Dram": 0.125,
        "Teaspoon": 0.16666666666667,
        "Tablespoon": 0.5,
        "Cubic Inch": 0.554113,
        "Fluid Ounce": 1.0,
        "Shot": 1.5,
        "Cup": 8.0,
        "Pint": 16.0,
        "Quart": 32.0,
        "Pottle": 64.0,
        "Gallon": 128.0,
        "Cubic Feet": 957.5065,
        "Barrel": 4032.0,
        "Butt": 16128,
        "Cubic Yard": 25852.68
    }
    
    conversion = round(value * units[from_unit] / units[to_unit], rounding)
    
    await ctx.respond(f"{value} {unit_shortcuts[from_unit]} is equal to {conversion} {unit_shortcuts[to_unit]}.")

    
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(convert_plugin)