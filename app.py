from decimal import InvalidOperation, localcontext
from pathlib import Path
from flask import Flask, redirect, render_template, request, url_for
from firma import Manager


def utworz_aplikacje(plik_danych=None):
    app = Flask(__name__)
    app.config['PLIK_DANYCH'] = Path(plik_danych) if plik_danych else Path(__file__).with_name('dane.txt')

    def wczytaj_managera():
        manager = Manager(app.config['PLIK_DANYCH'])
        manager.execute('wczytaj')
        return manager

    @app.route('/', methods=['GET', 'POST'])
    def glowna():
        blad = ''
        status = 200
        with localcontext() as kontekst:
            kontekst.prec = 60
            try:
                manager = wczytaj_managera()
            except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
                return render_template('blad.html', blad='Nie można odczytać pliku danych. Sprawdź dane.txt.'), 500
            if request.method == 'POST':
                try:
                    komenda = request.form.get('komenda', '')
                    if komenda not in ('saldo', 'zakup', 'sprzedaż'):
                        raise ValueError('Nieprawidłowa operacja.')
                    manager.formularz = request.form
                    manager.execute(komenda)
                    return redirect(url_for('glowna', zapisano=1))
                except (ValueError, InvalidOperation) as error:
                    blad = str(error)
                    status = 400
                except OSError:
                    blad = 'Nie udało się zapisać operacji. Sprawdź dostęp do pliku danych.'
                    status = 500
                # Po błędzie pokazujemy dane zapisane w pliku.
                manager = wczytaj_managera()
            return render_template('index.html', manager=manager, blad=blad,
                                   zapisano=request.args.get('zapisano') == '1',
                                   pola=request.form), status

    @app.route('/historia/')
    @app.route('/historia/<line_from>/<line_to>', strict_slashes=False)
    def historia(line_from=None, line_to=None):
        try:
            manager = wczytaj_managera()
        except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
            return render_template('blad.html', blad='Nie można odczytać pliku danych.'), 500
        blad = ''
        status = 200
        wpisy = list(enumerate(manager.historia))
        liczba = len(wpisy)
        if liczba:
            dostepny_zakres = f'Dostępny zakres indeksów: 0–{liczba - 1}.'
        else:
            dostepny_zakres = 'Historia jest pusta. Nie ma dostępnych indeksów.'
        if line_from is not None:
            try:
                line_from = int(line_from)
                line_to = int(line_to)
                if not 0 <= line_from <= line_to < liczba:
                    raise ValueError
                wpisy = wpisy[line_from:line_to + 1]
            except ValueError:
                blad = 'Nieprawidłowy zakres. ' + dostepny_zakres
                wpisy = []
                status = 400
        return render_template('historia.html', wpisy=wpisy, blad=blad,
                               liczba=liczba, od=line_from, do=line_to,
                               dostepny_zakres=dostepny_zakres), status

    @app.route('/historia/zakres/')
    def zakres():
        od = request.args.get('od', '')
        do = request.args.get('do', '')
        if not od and not do:
            return redirect(url_for('historia'))
        # Brak jednej granicy także kierujemy do strony z informacją o zakresie.
        return redirect(url_for('historia', line_from=od or 'brak', line_to=do or 'brak'))

    return app


if __name__ == '__main__':
    utworz_aplikacje().run(host='127.0.0.1', port=5000, threaded=False)
