import CustomMethodsVI.Parser.KVP as KVP


KEYMAP: str = '''
568=crater&S;aaxel&S;1&S;W&S
550=virgo&S;abrin&S;10&S;E&S
563=bootes&S;acjesis&S;11&S;R&S
565=centaurus&S;aldeni&S;12&S;T&S
570=libra&S;alura&S;13&S;Y&S
566=serpens_caput&S;amiwill&S;14&S;U&S
554=norma&S;arami&S;15&S;I&S
560=scorpius&S;avoniv&S;16&S;O&S
561=corona_australis&S;bydo&S;17&S;P&S
603=scutum&S;ca_po&S;18&S;[&S
605=sagittarius&S;danami&S;19&S;]&S
604=aquila&S;dawnre&S;2&S;\\&S

546=microscopium&S;ecrumig&S;20&S;A&S
564=capricornus&S;elenami&S;21&S;S&S
549=piscis_austrinus&S;gilltin&S;22&S;D&S
551=equuleus&S;hacemill&S;23&S;F&S
552=aquarius&S;hamlinto&S;24&S;G&S
553=pegasus&S;illume&S;25&S;H&S
555=sculptor&S;laylox&S;26&S;J&S
556=pisces&S;lenchan&S;27&S;K&S
557=andromeda&S;olavii&S;28&S;L&S
601=triangulum&S;once_el&S;29&S;%;&S
596=aries&S;poco_re&S;3&S;'x&S

571=perseus&S;ramnon&S;30&S;Z&S
569=cetus&S;recktic&S;31&S;X&S
548=auriga&S;robandus&S;32&S;C&S
567=taurus&S;roehi&S;33&S;V&S
547=eridanus&S;salma&S;34&S;B&S
559=orion&S;sandovi&S;35&S;N&S
558=canis_minor&S;setas&S;36&S;M&S
597=monoceros&S;sibbron&S;4&S;,&S
599=gemini&S;subido&S;5&S;.&S
600=lynx&S;tahnan&S;6&S;/&S

543=hydra&S;zamilloz&S;7&S;7&S
544=cancer&S;zeo&S;8&S;8&S
545=sextans&S;;9&S;9&S
536=leo_minor&S;;;0&S
598=leo&S;;;-&S
'''


if __name__ == '__main__':
	kvp: KVP.KVP = KVP.KVP.decode(KEYMAP)
	print(kvp.pretty_print(1))
